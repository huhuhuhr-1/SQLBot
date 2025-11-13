#!/bin/bash

# SQLBot MCP Adapter 启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python版本
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    if [[ $(echo "$PYTHON_VERSION < 3.8" | bc -l) -eq 1 ]]; then
        print_error "Python 3.8 or higher is required, found $PYTHON_VERSION"
        exit 1
    fi

    print_info "Python version: $PYTHON_VERSION ✓"
}

# 检查并安装依赖
install_dependencies() {
    print_info "Checking dependencies..."

    # 检查requirements.txt是否存在
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found"
        exit 1
    fi

    # 检查虚拟环境
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python3 -m venv venv
    fi

    # 激活虚拟环境
    source venv/bin/activate

    # 升级pip
    pip install --upgrade pip

    # 安装依赖
    print_info "Installing dependencies..."
    pip install -r requirements.txt

    print_success "Dependencies installed ✓"
}

# 检查环境配置
check_config() {
    print_info "Checking configuration..."

    if [ ! -f ".env" ]; then
        print_warning ".env file not found, copying from .env.example"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Please edit .env file with your SQLBot credentials"
        else
            print_error ".env.example file not found"
            exit 1
        fi
    fi

    # 检查必要的环境变量
    source .env

    if [ -z "$SQLBOT_USERNAME" ] || [ -z "$SQLBOT_PASSWORD" ]; then
        print_warning "SQLBOT_USERNAME or SQLBOT_PASSWORD not set in .env"
        print_info "Please update the .env file with your SQLBot credentials"
    fi

    print_success "Configuration checked ✓"
}

# 启动服务
start_service() {
    local mode=${1:-http}
    local host=${2:-0.0.0.0}
    local port=${3:-8080}

    print_info "Starting SQLBot MCP Adapter in $mode mode..."

    # 激活虚拟环境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    case $mode in
        "http")
            print_info "HTTP Server: http://$host:$port"
            print_info "MCP Endpoint: http://$host:$port/mcp"
            print_info "Health Check: http://$host:$port/health"
            echo
            python -m sqlbot_mcp_adapter.main --mode http --host $host --port $port
            ;;
        "stdio")
            print_info "Stdio mode started (for local development)"
            python -m sqlbot_mcp_adapter.main --mode stdio
            ;;
        *)
            print_error "Invalid mode: $mode. Use 'http' or 'stdio'"
            exit 1
            ;;
    esac
}

# 显示帮助信息
show_help() {
    echo "SQLBot MCP Adapter 启动脚本"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  install     安装依赖"
    echo "  check       检查环境和配置"
    echo "  http        启动HTTP模式 (默认)"
    echo "  stdio       启动Stdio模式"
    echo "  help        显示帮助信息"
    echo
    echo "环境变量:"
    echo "  HOST        HTTP服务器主机 (默认: 0.0.0.0)"
    echo "  PORT        HTTP服务器端口 (默认: 8080)"
    echo
    echo "示例:"
    echo "  $0                          # 启动HTTP模式"
    echo "  $0 http                    # 启动HTTP模式"
    echo "  $0 stdio                   # 启动Stdio模式"
    echo "  HOST=127.0.0.1 PORT=3000 $0 # 在127.0.0.1:3000启动"
}

# 主函数
main() {
    local command=${1:-http}

    print_info "SQLBot MCP Adapter 启动脚本"
    echo

    case $command in
        "install")
            check_python
            install_dependencies
            ;;
        "check")
            check_python
            check_config
            ;;
        "http")
            check_python
            install_dependencies
            check_config
            start_service "http" "${HOST:-0.0.0.0}" "${PORT:-8080}"
            ;;
        "stdio")
            check_python
            install_dependencies
            check_config
            start_service "stdio"
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# 捕获中断信号
trap 'print_info "Shutting down..."; exit 0' INT TERM

# 执行主函数
main "$@"