# Vertex AI Proxy

通过本地 OpenAI 兼容接口调用 Google Vertex AI 模型，利用浏览器会话认证。

## 功能

- OpenAI 格式 API，兼容 NextChat、Chatbox、LobeChat 等客户端
- 三种凭证模式：headless（自动化浏览器）、headful（浏览器脚本）、manual（手动）
- 自动检测 Token 过期并刷新
- 思考模式（-low/-high 后缀）
- 图片生成（-1k/-2k/-4k 后缀）
- SD WebUI 兼容 API
- 可选 GUI 界面

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

headless 模式需额外安装：

```bash
pip install playwright
playwright install chromium
```

### 启动

```bash
python main.py
```

服务地址：
- API: http://127.0.0.1:7860
- WebSocket: ws://127.0.0.1:7861（headful 模式）

### Docker 部署

#### 使用预构建镜像（推荐）

```bash
# 从 GitHub Container Registry 拉取镜像
docker pull ghcr.io/<your-username>/a-fandai-2:latest

# 运行容器
docker run -d \
  --name a-fandai-2 \
  -p 7860:7860 \
  -p 7861:7861 \
  -v ./config:/app/config \
  -v ./data:/app/data \
  ghcr.io/<your-username>/a-fandai-2:latest
```

#### 使用 docker-compose

```bash
docker-compose up -d
```

#### 本地构建

```bash
docker build -t vertex-ai-proxy .
docker run -d -p 7860:7860 -p 7861:7861 -v ./config:/app/config vertex-ai-proxy
```

### 客户端配置

| 配置项 | 值 |
|--------|-----|
| Base URL | http://127.0.0.1:7860/v1 |
| API Key | 任意值 |
| Model | gemini-2.5-pro 等 |

## 凭证模式

### headless（推荐）

自动化浏览器获取凭证，无需手动操作。

配置 config/config.json：

```json
{
  "credential_mode": "headless",
  "headless": {
    "show_browser": false,
    "auto_refresh_interval": 180
  }
}
```

首次运行需登录 Google 账号。设置 show_browser 为 true 可查看浏览器窗口。

### headful

使用 Tampermonkey 脚本获取凭证。

1. 安装 Tampermonkey 扩展
2. 添加 scripts/vertex-ai-harvester.user.js 脚本
3. 打开 Vertex AI Studio 并发送一条消息

### manual

使用已保存的凭证文件 config/credentials.json。

## 配置说明

### config/config.json

| 参数 | 说明 | 默认值 |
|------|------|--------|
| credential_mode | 凭证模式 | headful |
| enable_sd_api | 启用 SD WebUI API | true |
| enable_gui | 启用 GUI 窗口 | false |
| headless.show_browser | 显示浏览器 | false |
| headless.auto_refresh_interval | 刷新间隔（秒） | 180 |

### config/models.json

配置可用模型列表和别名映射。

支持的模型：
- gemini-2.5-pro
- gemini-2.5-flash-image
- gemini-2.0-flash-exp
- gemini-1.5-pro / gemini-1.5-flash
- gemini-3-pro-preview（思考模式）
- gemini-3-pro-image-preview（图片生成）

## 高级用法

### 思考模式

在模型名后添加后缀：
- -low：8K token 预算
- -high：32K token 预算

示例：gemini-3-pro-preview-low

### 图片生成

在模型名后添加后缀：
- -1k：1024x1024
- -2k：2048x2048
- -4k：4096x4096

示例：gemini-3-pro-image-preview-2k

## CI/CD

本项目使用 GitHub Actions 自动构建 Docker 镜像并推送到 GitHub Container Registry (GHCR)。

### 触发条件

- 推送到 `main` 或 `master` 分支
- 创建版本标签（如 `v1.0.0`）
- Pull Request 到 `main` 或 `master` 分支（仅构建，不推送）
- 手动触发

### 镜像标签

| 触发事件 | 镜像标签示例 |
|----------|--------------|
| 推送到 main | `latest`, `main`, `sha-abc1234` |
| 版本标签 v1.2.3 | `1.2.3`, `1.2`, `1`, `sha-abc1234` |
| Pull Request | 仅构建测试，不推送 |

### 支持的平台

- `linux/amd64`
- `linux/arm64`

## 项目结构

```
├── main.py                 # 入口
├── Dockerfile              # Docker 构建文件
├── docker-compose.yml      # Docker Compose 配置
├── docker-entrypoint.sh    # Docker 入口脚本
├── .dockerignore           # Docker 忽略文件
├── .github/
│   └── workflows/
│       └── docker-publish.yml  # GitHub Actions 工作流
├── config/
│   ├── config.json         # 主配置
│   ├── models.json         # 模型配置
│   └── credentials.json    # 凭证存储（自动生成）
├── scripts/
│   └── vertex-ai-harvester.user.js  # Tampermonkey 脚本
└── src/
    ├── api/                # API 路由
    ├── core/               # 核心模块
    ├── headless/           # 自动化浏览器
    └── stream/             # 流式处理
```

## 常见问题

**Token 过期提示**

保持 Vertex AI Studio 页面打开（headful 模式）或等待自动刷新（headless 模式）。

**浏览器脚本无响应**

确认在 console.cloud.google.com/vertex-ai 页面，脚本已启用。

**局域网访问**

服务监听 0.0.0.0，可使用本机局域网 IP 访问。

## 免责声明

仅供学习研究，请遵守 Google Cloud Platform 服务条款。