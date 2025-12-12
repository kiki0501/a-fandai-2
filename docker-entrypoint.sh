#!/bin/bash
set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 默认值
BROWSER_MODE=${BROWSER_MODE:-headless}
DISPLAY=${DISPLAY:-:99}

log_info "启动 Vertex AI Proxy..."
log_info "浏览器模式: $BROWSER_MODE"

# 如果是 headless 模式，启动 Xvfb 虚拟显示器
if [ "$BROWSER_MODE" = "headless" ]; then
    log_info "启动 Xvfb 虚拟显示器..."
    
    # 检查 Xvfb 是否已经在运行
    if ! pgrep -x "Xvfb" > /dev/null; then
        # 启动 Xvfb
        Xvfb $DISPLAY -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
        XVFB_PID=$!
        
        # 等待 Xvfb 启动
        sleep 2
        
        # 检查 Xvfb 是否成功启动
        if kill -0 $XVFB_PID 2>/dev/null; then
            log_info "Xvfb 已启动 (PID: $XVFB_PID, DISPLAY: $DISPLAY)"
        else
            log_error "Xvfb 启动失败"
            exit 1
        fi
    else
        log_info "Xvfb 已经在运行"
    fi
    
    export DISPLAY=$DISPLAY
fi

# 确保配置目录存在
mkdir -p /app/config/browser_data

# 设置正确的权限
chmod -R 755 /app/config 2>/dev/null || true

log_info "配置目录: /app/config"
log_info "浏览器数据目录: /app/config/browser_data"

# 检查配置文件
if [ -f "/app/config/config.json" ]; then
    log_info "找到配置文件: /app/config/config.json"
else
    log_warn "未找到配置文件，将使用默认配置"
fi

# 启动主应用
log_info "启动 Python 应用..."
exec python -m src.main "$@"