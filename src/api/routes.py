"""FastAPI路由模块"""

import asyncio
import json
import time
import uuid
from fastapi import FastAPI, Request, HTTPException, Security
from fastapi.responses import StreamingResponse, Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Any

from src.core import MODELS_CONFIG_FILE, TokenStatsManager, DISABLE_AUTH
from src.core.constants import ADMIN_API_KEY
from src.api.vertex_client import VertexAIClient
from src.core.auth import api_key_manager
from src.stream.processor import APIError, EmptyResponseError  # Import error exceptions


def extract_api_key_from_request(request: Request) -> str:
    """从请求中提取API密钥"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    # 对Authorization头进行trim处理，避免额外空格
    auth_header = auth_header.strip()
    
    if not auth_header.startswith("Bearer "):
        return None

    # 提取密钥并去除可能的前导/尾随空格
    # 使用split()而不是硬编码索引，更健壮
    api_key = auth_header[7:].strip()
    return api_key


def validate_admin_key(api_key: str) -> bool:
    """验证管理员密钥
    
    支持两种方式验证管理员权限：
    1. 通过 api_keys.txt 文件中配置的 admin_key
    2. 通过环境变量 ADMIN_API_KEY 设置的管理员密钥
    """
    if not api_key:
        return False

    # 方式1: 检查是否是 api_keys.txt 中配置的 admin_key
    key_info = api_key_manager.get_key_info(api_key)
    if key_info and key_info.get('name') == 'admin_key' and key_info.get('is_active'):
        return True
    
    # 方式2: 检查是否是环境变量设置的管理员密钥
    if ADMIN_API_KEY and api_key == ADMIN_API_KEY:
        return True
    
    return False


class APIKeyMiddleware(BaseHTTPMiddleware):
    """API密钥认证中间件"""

    def __init__(self, app, excluded_paths: list = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or ["/", "/health"]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 检查是否是完全排除的路径
        if path in self.excluded_paths:
            return await call_next(request)

        # 如果禁用了认证，直接放行
        if DISABLE_AUTH:
            # 设置默认的请求状态，避免后续代码出错
            request.state.api_key = "disabled"
            request.state.key_info = {"name": "auth_disabled", "is_active": True}
            return await call_next(request)

        # 获取API密钥
        api_key = extract_api_key_from_request(request)
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "缺少Authorization头"},
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 验证API密钥
        if not api_key_manager.validate_key(api_key):
            return JSONResponse(
                status_code=401,
                content={"detail": "无效的API密钥"},
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 将API密钥信息存储在请求状态中，供后续处理使用
        request.state.api_key = api_key
        request.state.key_info = api_key_manager.get_key_info(api_key)

        return await call_next(request)


class ConnectionCompatibilityMiddleware(BaseHTTPMiddleware):
    """
    连接兼容性中间件
    
    解决 httpx 等现代 HTTP 客户端的连接问题：
    - 确保正确的 Connection 头处理
    - 支持 HTTP/1.0 和 HTTP/1.1 客户端
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # 确保响应包含适当的连接头
        # 某些客户端（如 httpx）需要明确的 keep-alive 支持
        if "connection" not in response.headers:
            response.headers["Connection"] = "keep-alive"
        
        return response


def create_app(vertex_client: VertexAIClient, stats_manager: TokenStatsManager) -> FastAPI:
    """创建FastAPI应用"""
    app = FastAPI()

    # 添加API密钥认证中间件（放在最前面）
    app.add_middleware(APIKeyMiddleware, excluded_paths=["/", "/health"])

    # 添加连接兼容性中间件
    app.add_middleware(ConnectionCompatibilityMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
        expose_headers=["*"],  # 暴露所有响应头给客户端
    )



    @app.get("/")
    async def root():
        """根路径，返回服务信息"""
        return {
            "message": "Vertex AI Proxy Server",
            "version": "1.0.0",
            "auth": "API Key Authentication Required",
            "docs": "使用 Authorization: Bearer <api_key> 头进行认证"
        }

    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "healthy",
            "timestamp": int(time.time()),
            "api_keys_loaded": len(api_key_manager.api_keys)
        }
    
    @app.get("/v1/models")
    async def list_models():
        """返回可用模型列表"""
        current_time = int(time.time())
        models = []
        try:
            with open(MODELS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                models = config.get('models', [])
        except Exception as e:
            print(f"⚠️ 加载 models.json 失败: {e}")
            models = ["gemini-1.5-pro", "gemini-1.5-flash"]

        data = {
            "object": "list",
            "data": [
                {"id": m, "object": "model", "created": current_time, "owned_by": "google"}
                for m in models
            ]
        }
        return data

    # API密钥管理端点（需要管理员密钥）
    @app.get("/admin/api-keys")
    async def list_api_keys(request: Request):
        """列出所有API密钥（管理员功能）"""
        # 检查是否是管理员密钥
        if not validate_admin_key(request.state.api_key):
            raise HTTPException(status_code=403, detail="需要管理员权限")

        # 返回密钥统计信息（隐藏实际密钥）
        keys_summary = {}
        for key, info in api_key_manager.api_keys.items():
            keys_summary[info['name']] = {
                'description': info['description'],
                'created_at': info['created_at'],
                'usage_count': info['usage_count'],
                'last_used': info['last_used'],
                'is_active': info['is_active']
            }

        return {
            "stats": api_key_manager.get_stats(),
            "keys": keys_summary
        }

    @app.post("/admin/api-keys")
    async def create_api_key(request: Request):
        """创建新的API密钥（管理员功能）"""
        # 检查是否是管理员密钥
        if not validate_admin_key(request.state.api_key):
            raise HTTPException(status_code=403, detail="需要管理员权限")

        body = await request.json()
        key_name = body.get('name')
        description = body.get('description', '')

        if not key_name:
            raise HTTPException(status_code=400, detail="缺少密钥名称")

        # 检查名称是否已存在
        existing_names = [info['name'] for info in api_key_manager.api_keys.values()]
        if key_name in existing_names:
            raise HTTPException(status_code=400, detail="密钥名称已存在")

        new_key = api_key_manager.create_key(key_name, description)
        if not new_key:
            raise HTTPException(status_code=500, detail="创建密钥失败")

        return {
            "message": "API密钥创建成功",
            "api_key": new_key,
            "name": key_name,
            "description": description
        }

    @app.put("/admin/api-keys/{key_name}/status")
    async def update_key_status(key_name: str, request: Request):
        """更新API密钥状态（管理员功能）"""
        # 检查是否是管理员密钥
        if not validate_admin_key(request.state.api_key):
            raise HTTPException(status_code=403, detail="需要管理员权限")

        body = await request.json()
        is_active = body.get('is_active')

        if is_active is None:
            raise HTTPException(status_code=400, detail="缺少is_active参数")

        # 查找对应的API密钥
        target_key = None
        for key, info in api_key_manager.api_keys.items():
            if info['name'] == key_name:
                target_key = key
                break

        if not target_key:
            raise HTTPException(status_code=404, detail="密钥不存在")

        if is_active:
            success = api_key_manager.activate_key(target_key)
            status_msg = "激活"
        else:
            success = api_key_manager.deactivate_key(target_key)
            status_msg = "停用"

        if not success:
            raise HTTPException(status_code=500, detail="更新密钥状态失败")

        return {"message": f"API密钥 {status_msg}成功", "name": key_name, "is_active": is_active}

    @app.post("/admin/api-keys/reload")
    async def reload_api_keys(request: Request):
        """重新加载API密钥配置（管理员功能）"""
        # 检查是否是管理员密钥
        if not validate_admin_key(request.state.api_key):
            raise HTTPException(status_code=403, detail="需要管理员权限")

        success = api_key_manager.load_keys()
        if not success:
            raise HTTPException(status_code=500, detail="重新加载密钥失败")

        return {"message": "API密钥配置重新加载成功", "stats": api_key_manager.get_stats()}

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request):
        """处理聊天补全请求"""
        try:
            body = await request.json()
            messages = body.get('messages', [])
            model = body.get('model', 'gemini-1.5-pro')
            stream = body.get('stream', False)
            
            temperature = body.get('temperature')
            top_p = body.get('top_p')
            top_k = body.get('top_k')
            max_tokens = body.get('max_tokens')
            stop = body.get('stop')
            tools = body.get('tools')
            
            if not messages:
                if stream:
                    async def empty_stream_generator():
                        empty_chunk = {
                            "id": f"chatcmpl-proxy-empty-{uuid.uuid4()}",
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": "stop"}]
                        }
                        yield f"data: {json.dumps(empty_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                    return StreamingResponse(empty_stream_generator(), media_type="text/event-stream")
                else:
                    return {
                        "id": f"chatcmpl-proxy-empty-{uuid.uuid4()}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": model,
                        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                        "choices": [{
                            "index": 0,
                            "message": {"role": "assistant", "content": ""},
                            "finish_reason": "stop"
                        }]
                    }

            if stream:
                async def stream_with_disconnect_check():
                    """包装流式响应，添加客户端断开检测"""
                    try:
                        async for chunk in vertex_client.stream_chat(
                            messages,
                            model,
                            temperature=temperature,
                            top_p=top_p,
                            top_k=top_k,
                            max_tokens=max_tokens,
                            stop=stop,
                            tools=tools
                        ):
                            if await request.is_disconnected():
                                print("⚠️ 客户端断开，终止响应")
                                break
                            yield chunk
                    except APIError as e:
                        # API错误且无内容输出，返回500错误
                        print(f"⚠️ API错误: {str(e)}")
                        raise HTTPException(status_code=500, detail=str(e))
                    except EmptyResponseError as e:
                        # 上游空回复，返回505错误
                        print(f"⚠️ 上游空回复: {str(e)}")
                        raise HTTPException(status_code=505, detail=str(e))
                    except asyncio.CancelledError:
                        print("⚠️ 响应已取消")
                        raise
                
                # 增强的 SSE 响应头，提升 httpx 等客户端兼容性
                sse_headers = {
                    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
                    "Transfer-Encoding": "chunked",
                }
                
                return StreamingResponse(
                    stream_with_disconnect_check(),
                    media_type="text/event-stream",
                    headers=sse_headers
                )
            else:
                response_data = await vertex_client.complete_chat(
                    messages,
                    model,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k,
                    max_tokens=max_tokens,
                    stop=stop,
                    tools=tools
                )
                return response_data

        except HTTPException:
            raise
        except Exception as e:
            print(f"⚠️ 端点异常: {e}")
            raise HTTPException(status_code=500, detail={"error": str(e)})
    
    return app