# Sealos WSL 集群部署 Demo

本目录包含在 WSL 环境中使用 Sealos 部署 Kubernetes 集群的完整演示。

## 目录结构

```
demo/
├── install_sealos_wsl.sh           # 主要的 Sealos 安装脚本
├── install_sealos_wsl_final.sh     # 最终版本的安装脚本
├── sealos_solution.sh              # 网络问题解决方案脚本
├── configure_docker_mirrors.sh     # Docker 镜像加速器配置脚本
├── SEALOS_WSL_INSTALL_README.md    # 安装说明文档
├── Dockerfile_tmp                  # 临时 Dockerfile（参考）
├── SQLBot.jmx                      # JMeter 测试文件（参考）
├── SQLBot_OpenAPI_接口文档.md      # OpenAPI 接口文档（参考）
├── demo-app/                       # 示例应用源代码
│   └── Dockerfile                  # 应用 Docker 镜像构建文件
├── sealos-demo/                    # Sealos 集群镜像构建 Demo
│   ├── Clusterfile                 # 集群定义文件
│   ├── BUILD_INSTRUCTIONS.md       # 构建说明文档
│   ├── README.md                   # 基础说明
│   ├── deploy-demo.sh              # 应用部署脚本
│   └── manifests/                  # Kubernetes 资源定义
│       └── demo-app.yaml           # 应用部署定义
└── sealos-build/                   # SQLBot Sealos 镜像构建方案
    ├── Clusterfile                 # SQLBot 集群定义文件
    ├── sqlbot-k8s.yaml             # SQLBot Kubernetes 资源定义
    ├── build-docker-image.sh       # 构建 Docker 镜像脚本
    ├── deploy-sqlbot.sh            # 部署 SQLBot 脚本
    ├── README.md                   # 使用说明
    └── build-config.md             # 构建配置文档
```

## 主要功能

1. **WSL 兼容性解决方案** - 解决 Docker 与 Sealos 在 WSL 中的冲突
2. **网络优化** - 配置国内镜像源以加速镜像拉取
3. **应用示例** - 提供构建和部署自定义应用的示例
4. **错误恢复** - 完整的错误处理和 Docker 服务恢复机制

## 使用方法

### 1. 部署 Sealos 集群
```bash
# 确保 Docker 正常运行
docker ps

# 运行安装脚本
bash /opt/github/SQLBot/demo/install_sealos_wsl_final.sh
```

### 2. 构建自定义应用镜像
```bash
cd /opt/github/SQLBot/demo/demo-app
docker build -t demo-app:1.0 .
```

### 3. 部署应用到集群
```bash
# 在集群部署完成后
kubectl apply -f /opt/github/SQLBot/demo/sealos-demo/manifests/demo-app.yaml
```

### 4. 验证部署
```bash
kubectl get pods
kubectl get deployments
kubectl get services
```

## 注意事项

- 在 WSL 环境中，Docker 和 Sealos 存在 containerd 冲突
- 本解决方案通过临时重命名 containerd 文件来绕过检查
- 部署完成后会自动恢复 Docker 服务
- 建议使用国内镜像源以提高镜像拉取速度