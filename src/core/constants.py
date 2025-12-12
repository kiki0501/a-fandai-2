"""
核心常量定义模块

包含API端口、配置文件路径等全局常量。
"""

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