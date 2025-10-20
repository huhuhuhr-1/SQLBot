# SQLBot Sealos 镜像构建和部署指南

## 目录结构
```
sealos-build/
├── Clusterfile           # Sealos 集群定义文件
├── sqlbot-k8s.yaml       # SQLBot Kubernetes 资源定义
├── build-docker-image.sh # 构建 Docker 镜像脚本
├── deploy-sqlbot.sh      # 部署脚本
└── README.md             # 当前文档
```

## 构建和部署步骤

### 两种打包方式

Sealos 支持两种打包方式：

#### 方式1：应用镜像打包 (推荐)
这种方式只打包应用本身，适用于已有 Kubernetes 集群的场景：

**构建应用镜像包：**
```bash
# 构建应用 Docker 镜像
cd /opt/github/SQLBot
docker build -t dataease/sqlbot:latest .

# 创建应用包（包含部署文件）
bash /opt/github/SQLBot/sealos-build/package-app.sh
# 输出: sqlbot-app-v1.0.0.tar.gz
```

**部署到现有集群：**
```bash
# 方法1: 直接使用 kubectl
kubectl apply -f /opt/github/SQLBot/sealos-build/sqlbot-app.yaml

# 方法2: 使用打包文件中的部署配置
kubectl apply -f /opt/github/SQLBot/demo/sealos-build/sqlbot-app-v1.0.0/sqlbot-app/sqlbot-app.yaml
```

#### 方式2：完整集群镜像打包
这种方式打包完整的集群（包含 Kubernetes + 应用），适用于从零开始的场景：
```bash
# 构建应用 Docker 镜像
cd /opt/github/SQLBot
docker build -t dataease/sqlbot:latest .

# 使用部署脚本部署全新的集群（包含 Kubernetes + SQLBot）
bash /opt/github/SQLBot/sealos-build/deploy-sqlbot.sh full
```

### 部署到现有 Kubernetes 集群
```bash
# 如果您已经有运行的 Kubernetes 集群
bash /opt/github/SQLBot/sealos-build/deploy-sqlbot.sh existing
```

### 4. 验证部署
```bash
# 检查部署状态
bash /opt/github/SQLBot/sealos-build/deploy-sqlbot.sh verify
```

## 镜像构建高级选项

### 使用特定标签构建
```bash
# 构建带版本标签的镜像
docker build -t dataease/sqlbot:v1.2.0.20251020 .

# 推送到镜像仓库
docker tag dataease/sqlbot:v1.2.0.20251020 your-registry/sqlbot:v1.2.0.20251020
docker push your-registry/sqlbot:v1.2.0.20251020
```

### 在 Clusterfile 中添加自定义镜像
如果需要添加自定义镜像，可以修改 Clusterfile：
```yaml
apiVersion: apps.sealos.io/v1beta1
kind: Cluster
metadata:
  name: sqlbot-cluster
spec:
  image:
    - swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/kubernetes:v1.28.0
    - swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/calico:v3.26.5
---
apiVersion: apps.sealos.io/v1beta1
kind: ImageList
metadata:
  name: custom-images
spec:
  images:
    - dataease/sqlbot:latest  # Add your custom image here
---
apiVersion: apps.sealos.io/v1beta1
kind: Applier
metadata:
  name: sqlbot-applier
spec:
  manifests:
    - sqlbot-k8s.yaml
```

## 应用访问

部署完成后，您可以通过以下方式访问 SQLBot：

1. **API 访问**: `http://<node-ip>:30000`
2. **UI 访问**: `http://<node-ip>:30001`
3. **Ingress 访问**: `http://sqlbot.local` (需要在 `/etc/hosts` 中添加映射)

## 配置自定义

您可以根据需要修改以下配置：

1. **环境变量**: 修改 `sqlbot-k8s.yaml` 中的 ConfigMap
2. **资源需求**: 在 Deployment 中调整 resources 限制
3. **存储配置**: 修改 PVC 的存储大小
4. **网络配置**: 修改 Service 和 Ingress 设置

## WSL 特殊说明

在 WSL 环境中部署时，脚本会自动处理 Docker 和 Sealos 的冲突问题：
- 临时重命名 containerd 相关文件以绕过 Sealos 检查
- 部署完成后自动恢复 Docker 服务
- 保护您的 Docker 环境不受影响

## 故障排除

如果部署失败：

1. 检查 Docker 和 Sealos 是否正常安装
2. 确保有足够的磁盘空间
3. 检查网络连接是否正常
4. 查看脚本输出的错误信息

如需清理部署，可以使用：
```bash
kubectl delete namespace sqlbot
```