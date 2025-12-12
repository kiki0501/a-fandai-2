# Vertex AI Proxy Docker 镜像
# 支持 headless 浏览器自动化模式

FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DISPLAY=:99

# 安装系统依赖（包括 Playwright 和 Xvfb 所需的依赖）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Xvfb 虚拟显示器
    xvfb \
    # Playwright/Chromium 依赖
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    # 字体支持
    fonts-liberation \
    fonts-noto-cjk \
    # 网络工具
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 和浏览器
RUN pip install playwright && \
    playwright install chromium && \
    playwright install-deps chromium

# 复制应用代码
COPY . .

# 复制并设置入口脚本权限
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# 创建配置目录
RUN mkdir -p config/browser_data

# 暴露端口
EXPOSE 7860

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7860/v1/models || exit 1

# 入口点
ENTRYPOINT ["/docker-entrypoint.sh"]