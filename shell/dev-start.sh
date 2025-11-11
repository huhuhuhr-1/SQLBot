#!/bin/bash

# SQLBot开发环境快速启动脚本

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

# 检查Docker是否运行
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker未运行，请先启动Docker"
        exit 1
    fi
}

# 检查镜像是否存在
check_image() {
    if ! docker images -q sqlbot-dev:latest | grep -q .; then
        print_warning "sqlbot-dev:latest镜像不存在，开始构建..."
        build_image
    fi
}

# 构建镜像
build_image() {
    print_info "构建SQLBot开发环境镜像..."
    if docker build -f Dockerfile.dev -t sqlbot-dev:latest .; then
        print_success "镜像构建完成"
    else
        print_error "镜像构建失败"
        exit 1
    fi
}

# 启动开发环境
start_dev() {
    print_info "启动SQLBot开发环境..."

    # 停止并删除已存在的容器
    if docker ps -aqf name=sqlbot-dev | grep -q .; then
        print_warning "发现已存在的sqlbot-dev容器，正在停止并删除..."
        docker stop sqlbot-dev > /dev/null 2>&1 || true
        docker rm sqlbot-dev > /dev/null 2>&1 || true
    fi

    # 创建并启动容器
    docker run -d --name sqlbot-dev \
        -p 8000:8000 \
        -p 3000:3000 \
        -p 8001:8001 \
        -v "$(pwd)/backend:/workspace/sqlbot/backend" \
        -v "$(pwd)/frontend:/workspace/sqlbot/frontend" \
        -v "$(pwd)/g2-ssr:/workspace/sqlbot/g2-ssr" \
        sqlbot-dev:latest

    if [ $? -eq 0 ]; then
        print_success "SQLBot开发环境已启动"
        show_info
    else
        print_error "启动开发环境失败"
        exit 1
    fi
}

# 交互模式启动
start_interactive() {
    print_info "以交互模式启动SQLBot开发环境..."

    # 停止并删除已存在的容器
    if docker ps -aqf name=sqlbot-dev | grep -q .; then
        print_warning "发现已存在的sqlbot-dev容器，正在停止并删除..."
        docker stop sqlbot-dev > /dev/null 2>&1 || true
        docker rm sqlbot-dev > /dev/null 2>&1 || true
    fi

    # 创建并启动容器（交互模式）
    docker run -it --name sqlbot-dev \
        -p 8000:8000 \
        -p 3000:3000 \
        -p 8001:8001 \
        -v "$(pwd)/backend:/workspace/sqlbot/backend" \
        -v "$(pwd)/frontend:/workspace/sqlbot/frontend" \
        -v "$(pwd)/g2-ssr:/workspace/sqlbot/g2-ssr" \
        sqlbot-dev:latest bash
}

# 停止开发环境
stop_dev() {
    print_info "停止SQLBot开发环境..."
    if docker ps -qf name=sqlbot-dev | grep -q .; then
        docker stop sqlbot-dev
        print_success "SQLBot开发环境已停止"
    else
        print_warning "sqlbot-dev容器未运行"
    fi
}

# 进入容器
enter_container() {
    if docker ps -qf name=sqlbot-dev | grep -q .; then
        print_info "进入sqlbot-dev容器..."
        docker exec -it sqlbot-dev bash
    else
        print_error "sqlbot-dev容器未运行，请先启动开发环境"
        exit 1
    fi
}

# 显示信息
show_info() {
    echo ""
    print_success "=== SQLBot开发环境信息 ==="
    echo -e "${BLUE}容器名称:${NC} sqlbot-dev"
    echo -e "${BLUE}服务端口:${NC}"
    echo "  - 后端API: http://localhost:8000"
    echo "  - 前端页面: http://localhost:3000"
    echo "  - G2-SSR: http://localhost:8001"
    echo ""
    echo -e "${BLUE}常用命令:${NC}"
    echo "  进入容器: $0 enter"
    echo "  停止环境: $0 stop"
    echo "  重启环境: $0 restart"
    echo "  交互启动: $0 interactive"
    echo ""
    echo -e "${BLUE}容器内开发命令:${NC}"
    echo "  启动后端: cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
    echo "  启动前端: cd frontend && npm run dev"
    echo "  启动G2-SSR: cd g2-ssr && npm start"
    echo ""
}

# 显示帮助
show_help() {
    echo "SQLBot开发环境管理脚本"
    echo ""
    echo "用法: $0 [命令]"
    echo ""
    echo "命令:"
    echo "  start       启动开发环境（默认）"
    echo "  interactive 交互模式启动"
    echo "  stop        停止开发环境"
    echo "  restart     重启开发环境"
    echo "  enter       进入容器"
    echo "  build       构建镜像"
    echo "  status      查看状态"
    echo "  help        显示此帮助信息"
    echo ""
}

# 查看状态
show_status() {
    echo "=== Docker镜像状态 ==="
    docker images | grep sqlbot-dev || echo "sqlbot-dev镜像不存在"
    echo ""
    echo "=== 容器状态 ==="
    if docker ps -af name=sqlbot-dev | grep -q .; then
        docker ps -af name=sqlbot-dev
    else
        echo "sqlbot-dev容器不存在"
    fi
}

# 主函数
main() {
    case "${1:-start}" in
        "start")
            check_docker
            check_image
            start_dev
            ;;
        "interactive")
            check_docker
            check_image
            start_interactive
            ;;
        "stop")
            stop_dev
            ;;
        "restart")
            stop_dev
            sleep 2
            check_docker
            check_image
            start_dev
            ;;
        "enter")
            enter_container
            ;;
        "build")
            check_docker
            build_image
            ;;
        "status")
            show_status
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"