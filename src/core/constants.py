"""
核心常量定义模块

包含API端口、配置文件路径等全局常量。
"""

import os

# API和WebSocket服务端口
PORT_API = 7860
PORT_WS = 7861

# 最大并发上游请求数（Semaphore 限流）
# 超过此数量的请求将进入等待队列
MAX_CONCURRENT_REQUESTS = 4

# 配置文件路径 (已移至 config/ 文件夹)
MODELS_CONFIG_FILE = "config/models.json"
STATS_FILE = "config/stats.json"
CONFIG_FILE = "config/config.json"
CREDENTIALS_FILE = "config/credentials.json"


def _parse_bool_env(env_name: str, default: bool = False) -> bool:
    """
    解析布尔类型的环境变量
    
    Args:
        env_name: 环境变量名称
        default: 默认值
        
    Returns:
        解析后的布尔值
    """
    value = os.environ.get(env_name, "").lower().strip()
    if value in ("true", "1", "yes"):
        return True
    elif value in ("false", "0", "no"):
        return False
    return default


# 认证配置
# 通过环境变量 DISABLE_AUTH 控制是否禁用认证
# 设置为 "true", "1", "yes" 时禁用认证，允许无 API Key 访问
DISABLE_AUTH = _parse_bool_env("DISABLE_AUTH", False)