# API密钥使用示例

## 配置说明

API密钥存储在 `config/api_keys.txt` 文件中，格式为：
```
key_name:api_key:description
```

## 认证方式

所有API请求都需要在HTTP头中包含有效的API密钥：
```
Authorization: Bearer sk-your-api-key-here
```

## API端点

### 公开端点（无需认证）
- `GET /` - 服务信息
- `GET /health` - 健康检查
- `GET /v1/models` - 模型列表

### 受保护端点（需要API密钥）
- `POST /v1/chat/completions` - 聊天补全

### 管理端点（需要admin_key）
- `GET /admin/api-keys` - 列出所有API密钥
- `POST /admin/api-keys` - 创建新API密钥
- `PUT /admin/api-keys/{key_name}/status` - 更新密钥状态
- `POST /admin/api-keys/reload` - 重新加载密钥配置

## 使用示例

### 1. 使用curl测试API

```bash
# 获取模型列表（无需认证）
curl http://localhost:8080/v1/models

# 使用API密钥进行聊天补全
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-demo-2024-vertex-proxy" \
  -d '{
    "model": "gemini-1.5-pro",
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'

# 使用管理员密钥创建新API密钥
curl -X POST http://localhost:8080/admin/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-2024-vertex-proxy" \
  -d '{
    "name": "new_client",
    "description": "新的客户端密钥"
  }'
```

### 2. 使用Python客户端

```python
import requests

# API配置
BASE_URL = "http://localhost:8080"
API_KEY = "sk-demo-2024-vertex-proxy"

# 设置请求头
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 发送聊天请求
response = requests.post(
    f"{BASE_URL}/v1/chat/completions",
    headers=headers,
    json={
        "model": "gemini-1.5-pro",
        "messages": [
            {"role": "user", "content": "请介绍一下你自己"}
        ]
    }
)

print(response.json())
```

### 3. 使用OpenAI兼容客户端库

```python
from openai import OpenAI

# 配置客户端
client = OpenAI(
    api_key="sk-demo-2024-vertex-proxy",
    base_url="http://localhost:8080/v1"
)

# 发送聊天请求
response = client.chat.completions.create(
    model="gemini-1.5-pro",
    messages=[
        {"role": "user", "content": "你好！"}
    ]
)

print(response.choices[0].message.content)
```

## 预定义密钥

系统预定义了以下API密钥：

| 密钥名称 | API密钥 | 描述 |
|---------|---------|------|
| admin_key | sk-admin-2024-vertex-proxy | 管理员完全访问权限 |
| client_demo | sk-demo-2024-vertex-proxy | 演示客户端密钥 |
| client_user1 | sk-user1-2024-vertex-proxy | 用户1的访问密钥 |
| client_user2 | sk-user2-2024-vertex-proxy | 用户2的访问密钥 |
| internal_service | sk-internal-2024-vertex-proxy | 内部服务调用密钥 |
| test_key | sk-test-2024-vertex-proxy | 测试环境专用密钥 |

## 安全建议

1. **定期更换密钥**: 建议定期更换API密钥以提高安全性
2. **最小权限原则**: 根据需要创建不同权限的密钥
3. **监控使用情况**: 使用管理员端点监控密钥使用情况
4. **停用不用的密钥**: 及时停用不再使用的密钥
5. **保护密钥安全**: 不要在代码中硬编码API密钥