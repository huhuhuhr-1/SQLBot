#!/bin/bash

# SQLBot开发环境配置示例
# 使用方法: source config-examples.sh

echo "=== SQLBot开发环境配置示例 ==="
echo ""

# 示例1: 使用自定义端口启动
echo "示例1: 自定义端口启动"
echo "./dev-start-enhanced.sh start --backend-port 8080 --frontend-port 3001 --ssr-port 8002"
echo ""

# 示例2: 使用清华源启动
echo "示例2: 使用清华源"
echo "./dev-start-enhanced.sh start --use-tsinghua"
echo ""

# 示例3: 自定义源
echo "示例3: 自定义源"
echo "./dev-start-enhanced.sh start --pip-source https://pypi.douban.com/simple/ --npm-source https://registry.npm.taobao.org"
echo ""

# 示例4: 完全自定义配置
echo "示例4: 完全自定义配置"
echo "./dev-start-enhanced.sh start \\"
echo "  --backend-port 9000 \\"
echo "  --frontend-port 9001 \\"
echo "  --ssr-port 9002 \\"
echo "  --host 127.0.0.1 \\"
echo "  --pip-source https://mirrors.163.com/pypi/simple/ \\"
echo "  --npm-source https://registry.npmmirror.com"
echo ""

# 示例5: 交互模式使用自定义端口
echo "示例5: 交互模式"
echo "./dev-start-enhanced.sh interactive --use-aliyun --frontend-port 3000"
echo ""

# 示例6: 外网访问配置
echo "示例6: 外网访问配置"
echo "./dev-start-enhanced.sh start --host 0.0.0.0"
echo "然后在路由器配置端口转发:"
echo "  外网端口8080 -> 内网IP:8000 (后端)"
echo "  外网端口8081 -> 内网IP:3000 (前端)"
echo "  外网端口8082 -> 内网IP:8001 (SSR)"
echo ""

# 示例7: 容器内源管理
echo "示例7: 容器内源管理命令"
echo "# 进入容器"
echo "./dev-start-enhanced.sh enter"
echo ""
echo "# 在容器内:"
echo "sources show_sources                    # 查看当前源"
echo "aliyun                                  # 切换阿里云源"
echo "tsinghua                                # 切换清华源"
echo "official                                # 切换官方源"
echo "sources set_pip_source https://pypi.org/simple/  # 自定义pip源"
echo "sources set_npm_source https://registry.npmjs.org # 自定义npm源"
echo ""

# 示例8: 端口管理
echo "示例8: 容器内端口管理"
echo "# 进入容器"
echo "./dev-start-enhanced.sh enter"
echo ""
echo "# 在容器内:"
echo "ports                                    # 显示SQLBot端口状态"
echo "port-manager.sh check_port 8000          # 检查特定端口"
echo ""

echo "=== 环境变量配置 ==="
echo "也可以通过环境变量配置:"
echo ""
echo "export BACKEND_PORT=8080"
echo "export FRONTEND_PORT=3001"
echo "export SSR_PORT=8002"
echo "./dev-start-enhanced.sh start"
echo ""

echo "=== 生产环境映射示例 ==="
echo "# 假设服务器IP为 192.168.1.100"
echo "docker run -d --name sqlbot-prod \\"
echo "  -p 192.168.1.100:80:8000 \\"
echo "  -p 192.168.1.100:443:3000 \\"
echo "  -p 192.168.1.100:8081:8001 \\"
echo "  -v /path/to/sqlbot:/workspace/sqlbot \\"
echo "  sqlbot-dev-enhanced:latest"
echo ""

echo "=== 开发技巧 ==="
echo "1. 使用 --use-official 当需要安装最新包时"
echo "2. 使用 --use-aliyun 或 --use-tsinghua 提高下载速度"
echo "3. 端口冲突时使用 --backend-port 等参数调整"
echo "4. 外网访问时确保防火墙开放对应端口"
echo "5. 使用 docker logs sqlbot-dev-enhanced 查看日志"
echo ""