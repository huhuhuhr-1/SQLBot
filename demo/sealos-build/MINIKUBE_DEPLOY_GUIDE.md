# 在 Minikube 中部署 SQLBot 应用

## 环境要求
- Docker
- kubectl
- minikube
- 本目录中的文件:
  - `sqlbot-app-v1.0.0.tar.gz` (应用包)
  - `sqlbot-app.yaml` (部署配置)

## 安装 Minikube (如果尚未安装)

### 在 Linux 上安装 Minikube:
```bash
# 下载并安装 minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
```

### 或使用包管理器:
```bash
# Ubuntu/Debian
curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
chmod +x minikube
sudo mv minikube /usr/local/bin/
```

## 部署步骤

### 1. 启动 Minikube 集群
```bash
# 使用 Docker 驱动启动 Minikube
minikube start --driver=docker
```

### 2. 确认集群运行
```bash
# 检查集群状态
kubectl cluster-info

# 检查节点
kubectl get nodes
```

### 3. 部署 SQLBot 应用
```bash
# 方式1: 使用应用包部署
kubectl apply -f /opt/github/SQLBot/demo/sealos-build/sqlbot-app.yaml

# 方式2: 使用本地构建的 Docker 镜像
# 让 Minikube 使用本地 Docker 镜像
eval $(minikube docker-env)
# 然后应用配置
kubectl apply -f /opt/github/SQLBot/demo/sealos-build/sqlbot-app.yaml
```

### 4. 验证部署
```bash
# 检查命名空间
kubectl get namespaces

# 检查 SQLBot 部署
kubectl get deployments -n sqlbot

# 检查 SQLBot 服务
kubectl get services -n sqlbot

# 检查 SQLBot Pod
kubectl get pods -n sqlbot

# 查看日志
kubectl logs -n sqlbot -l app=sqlbot
```

## 访问应用

### 获取服务 URL
```bash
# 获取 NodePort 服务的访问 URL
minikube service sqlbot-service -n sqlbot --url
```

### 或使用端口转发
```bash
# 本地访问
kubectl port-forward -n sqlbot service/sqlbot-service 8000:8000 8001:8001
```

## 常见问题

### 1. 镜像拉取问题
如果遇到镜像拉取问题，使用本地镜像环境：
```bash
# 设置 Minikube 使用本地 Docker 环境
eval $(minikube docker-env)
# 重新构建镜像以确保 Minikube 可以访问
docker build -t dataease/sqlbot:latest .
```

### 2. 资源不足
增加 Minikube 资源：
```bash
minikube start --driver=docker --memory=6g --cpus=4
```

### 3. 存储问题
如果遇到存储问题，确保有足够磁盘空间：
```bash
# 检查 Minikube 磁盘使用
minikube ssh 'df -h'
```

## 清理
```bash
# 停止 Minikube
minikube stop

# 删除 Minikube 集群
minikube delete
```

## 生产环境部署

在生产环境中，您可以通过以下方式部署：

1. **直接部署**: `kubectl apply -f sqlbot-app.yaml`
2. **Helm Chart**: 包装为 Helm Chart 进行管理
3. **GitOps**: 使用 ArgoCD 或 Flux 进行持续部署
4. **云服务**: 部署到 EKS, AKS, GKE 等托管服务

## 验证部署
```bash
# 检查所有资源
kubectl get all -n sqlbot

# 检查存储
kubectl get pvc -n sqlbot

# 检查配置
kubectl get configmaps -n sqlbot
```

## 故障排除
```bash
# 描述 Pod 以获取详细信息
kubectl describe pod -n sqlbot -l app=sqlbot

# 查看详细事件
kubectl get events -n sqlbot --sort-by='.lastTimestamp'

# 检查服务端口
kubectl get svc -n sqlbot -o yaml
```

您的 SQLBot 应用包 `sqlbot-app-v1.0.0.tar.gz` 是完全可移植和功能完整的，可以在任何 Kubernetes 环境中部署！