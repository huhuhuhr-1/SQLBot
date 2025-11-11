#!/bin/bash

# SQLBot增强开发环境快速启动脚本 - 支持自定义源和端口

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 默认配置
DEFAULT_BACKEND_PORT=8000
DEFAULT_FRONTEND_PORT=3000
DEFAULT_SSR_PORT=8001
DEFAULT_HOST=0.0.0.0

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

print_header() {
    echo -e "${PURPLE}=== $1 ===${NC}"
}

# 显示帮助
show_help() {
    echo "SQLBot增强开发环境管理脚本"
    echo ""
    echo "用法: $0 [命令] [选项]"
    echo ""
    echo "基本命令:"
    echo "  start                  启动开发环境（默认）"
    echo "  interactive            交互模式启动"
    echo "  stop                   停止开发环境"
    echo "  restart                重启开发环境"
    echo "  enter                  进入容器"
    echo "  build                  构建镜像"
    echo "  status                 查看状态"
    echo "  help                   显示此帮助信息"
    echo ""
    echo "端口配置:"
    echo "  --backend-port PORT    后端API端口 (默认: 8000)"
    echo "  --frontend-port PORT   前端页面端口 (默认: 3000)"
    echo "  --ssr-port PORT        G2-SSR端口 (默认: 8001)"
    echo "  --host HOST            绑定主机 (默认: 0.0.0.0)"
    echo ""
    echo "源配置:"
    echo "  --pip-source URL       pip源URL"
    echo "  --npm-source URL       npm源URL"
    echo "  --use-official         使用官方源"
    echo "  --use-aliyun           使用阿里云源"
    echo "  --use-tsinghua         使用清华源"
    echo ""
    echo "示例:"
    echo "  $0 start                               # 默认配置启动"
    echo "  $0 start --backend-port 8080          # 后端使用8080端口"
    echo "  $0 start --use-tsinghua               # 使用清华源"
    echo "  $0 start --pip-source https://pypi.org/simple/ --frontend-port 3001"
    echo ""
}

# 检查Docker是否运行
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker未运行，请先启动Docker"
        exit 1
    fi
}

# 检查端口是否被占用
check_port_available() {
    local port=$1
    if lsof -i :$port > /dev/null 2>&1; then
        print_warning "端口 $port 已被占用"
        return 1
    else
        return 0
    fi
}

# 检查镜像是否存在
check_image() {
    local image_name=${1:-sqlbot-dev-enhanced:latest}
    if ! docker images -q $image_name | grep -q .; then
        print_warning "$image_name 镜像不存在，开始构建..."
        build_image $image_name
    fi
}

# 构建镜像
build_image() {
    local image_name=${1:-sqlbot-dev-enhanced:latest}
    local dockerfile="Dockerfile.dev.enhanced"

    print_header "构建SQLBot增强开发环境镜像"

    # 构建参数
    local build_args=""
    if [ -n "$PIP_SOURCE" ]; then
        build_args="$build_args --build-arg PIP_INDEX_URL=$PIP_SOURCE"
    fi
    if [ -n "$NPM_SOURCE" ]; then
        build_args="$build_args --build-arg NPM_REGISTRY=$NPM_SOURCE"
    fi

    print_info "构建参数: $build_args"
    print_info "Dockerfile: $dockerfile"
    print_info "镜像名称: $image_name"

    if eval "docker build -f $dockerfile $build_args -t $image_name ."; then
        print_success "镜像构建完成"
    else
        print_error "镜像构建失败"
        exit 1
    fi
}

# 启动开发环境
start_dev() {
    local image_name="sqlbot-dev-enhanced:latest"
    local container_name="sqlbot-dev-enhanced"

    print_header "启动SQLBot增强开发环境"

    # 检查端口可用性
    check_port_available $BACKEND_PORT || true
    check_port_available $FRONTEND_PORT || true
    check_port_available $SSR_PORT || true

    # 停止并删除已存在的容器
    if docker ps -aqf name=$container_name | grep -q .; then
        print_warning "发现已存在的$container_name容器，正在停止并删除..."
        docker stop $container_name > /dev/null 2>&1 || true
        docker rm $container_name > /dev/null 2>&1 || true
    fi

    # 端口映射
    local port_mappings=""
    port_mappings="-p $BACKEND_PORT:$BACKEND_PORT"
    port_mappings="$port_mappings -p $FRONTEND_PORT:$FRONTEND_PORT"
    port_mappings="$port_mappings -p $SSR_PORT:$SSR_PORT"

    # 环境变量
    local env_vars=""
    env_vars="-e BACKEND_PORT=$BACKEND_PORT"
    env_vars="$env_vars -e FRONTEND_PORT=$FRONTEND_PORT"
    env_vars="$env_vars -e SSR_PORT=$SSR_PORT"

    # 创建并启动容器
    print_info "端口映射: $port_mappings"
    print_info "环境变量: $env_vars"

    if docker run -d --name $container_name \
        $port_mappings \
        $env_vars \
        -v "$(pwd)/backend:/workspace/sqlbot/backend" \
        -v "$(pwd)/frontend:/workspace/sqlbot/frontend" \
        -v "$(pwd)/g2-ssr:/workspace/sqlbot/g2-ssr" \
        $image_name; then

        print_success "SQLBot增强开发环境已启动"
        show_enhanced_info
    else
        print_error "启动开发环境失败"
        exit 1
    fi
}

# 交互模式启动
start_interactive() {
    local image_name="sqlbot-dev-enhanced:latest"
    local container_name="sqlbot-dev-enhanced"

    print_header "交互模式启动SQLBot增强开发环境"

    # 停止并删除已存在的容器
    if docker ps -aqf name=$container_name | grep -q .; then
        print_warning "发现已存在的$container_name容器，正在停止并删除..."
        docker stop $container_name > /dev/null 2>&1 || true
        docker rm $container_name > /dev/null 2>&1 || true
    fi

    # 环境变量
    local env_vars=""
    env_vars="-e BACKEND_PORT=$BACKEND_PORT"
    env_vars="$env_vars -e FRONTEND_PORT=$FRONTEND_PORT"
    env_vars="$env_vars -e SSR_PORT=$SSR_PORT"

    print_info "交互模式启动，将直接进入容器..."
    docker run -it --name $container_name \
        -p $BACKEND_PORT:$BACKEND_PORT \
        -p $FRONTEND_PORT:$FRONTEND_PORT \
        -p $SSR_PORT:$SSR_PORT \
        $env_vars \
        -v "$(pwd)/backend:/workspace/sqlbot/backend" \
        -v "$(pwd)/frontend:/workspace/sqlbot/frontend" \
        -v "$(pwd)/g2-ssr:/workspace/sqlbot/g2-ssr" \
        $image_name bash
}

# 停止开发环境
stop_dev() {
    local container_name="sqlbot-dev-enhanced"
    print_info "停止SQLBot增强开发环境..."
    if docker ps -qf name=$container_name | grep -q .; then
        docker stop $container_name
        print_success "SQLBot增强开发环境已停止"
    else
        print_warning "$container_name容器未运行"
    fi
}

# 进入容器
enter_container() {
    local container_name="sqlbot-dev-enhanced"
    if docker ps -qf name=$container_name | grep -q .; then
        print_info "进入$container_name容器..."
        docker exec -it $container_name bash
    else
        print_error "$container_name容器未运行，请先启动开发环境"
        exit 1
    fi
}

# 显示增强信息
show_enhanced_info() {
    echo ""
    print_success "=== SQLBot增强开发环境信息 ==="
    echo -e "${BLUE}容器名称:${NC} sqlbot-dev-enhanced"
    echo -e "${BLUE}服务端口:${NC}"
    echo "  - 后端API: http://localhost:$BACKEND_PORT"
    echo "  - 前端页面: http://localhost:$FRONTEND_PORT"
    echo "  - G2-SSR: http://localhost:$SSR_PORT"
    echo ""
    echo -e "${BLUE}源配置:${NC}"
    if [ -n "$PIP_SOURCE" ]; then
        echo "  pip源: $PIP_SOURCE"
    fi
    if [ -n "$NPM_SOURCE" ]; then
        echo "  npm源: $NPM_SOURCE"
    fi
    echo ""
    echo -e "${BLUE}常用命令:${NC}"
    echo "  进入容器: $0 enter"
    echo "  停止环境: $0 stop"
    echo "  重启环境: $0 restart"
    echo "  交互启动: $0 interactive"
    echo ""
    echo -e "${BLUE}容器内增强功能:${NC}"
    echo "  源管理命令: sources (aliyun|tsinghua|official)"
    echo "  端口管理: ports"
    echo "  查看当前源: sources show_sources"
    echo "  切换阿里云源: aliyun"
    echo "  切换清华源: tsinghua"
    echo "  切换官方源: official"
    echo ""
    echo -e "${BLUE}容器内开发命令:${NC}"
    echo "  启动后端: cd backend && uvicorn main:app --host $HOST --port $BACKEND_PORT --reload"
    echo "  启动前端: cd frontend && npm run dev -- --port $FRONTEND_PORT"
    echo "  启动G2-SSR: cd g2-ssr && PORT=$SSR_PORT npm start"
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
    echo ""
    echo "=== 当前端口配置 ==="
    echo "后端端口: $BACKEND_PORT"
    echo "前端端口: $FRONTEND_PORT"
    echo "SSR端口: $SSR_PORT"
    echo "绑定主机: $HOST"
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backend-port)
                BACKEND_PORT="$2"
                shift 2
                ;;
            --frontend-port)
                FRONTEND_PORT="$2"
                shift 2
                ;;
            --ssr-port)
                SSR_PORT="$2"
                shift 2
                ;;
            --host)
                HOST="$2"
                shift 2
                ;;
            --pip-source)
                PIP_SOURCE="$2"
                shift 2
                ;;
            --npm-source)
                NPM_SOURCE="$2"
                shift 2
                ;;
            --use-official)
                PIP_SOURCE="https://pypi.org/simple/"
                NPM_SOURCE="https://registry.npmjs.org"
                shift
                ;;
            --use-aliyun)
                PIP_SOURCE="https://mirrors.aliyun.com/pypi/simple/"
                NPM_SOURCE="https://registry.npmmirror.com"
                shift
                ;;
            --use-tsinghua)
                PIP_SOURCE="https://pypi.tuna.tsinghua.edu.cn/simple/"
                NPM_SOURCE="https://registry.npmmirror.com"
                shift
                ;;
            start|interactive|stop|restart|enter|build|status|help)
                COMMAND="$1"
                shift
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# 主函数
main() {
    # 设置默认值
    BACKEND_PORT=${BACKEND_PORT:-$DEFAULT_BACKEND_PORT}
    FRONTEND_PORT=${FRONTEND_PORT:-$DEFAULT_FRONTEND_PORT}
    SSR_PORT=${SSR_PORT:-$DEFAULT_SSR_PORT}
    HOST=${HOST:-$DEFAULT_HOST}
    COMMAND=${COMMAND:-"start"}

    # 解析参数
    parse_args "$@"

    case "$COMMAND" in
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
            print_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"