# Sealos 集群镜像构建说明

## 目录结构
```
sealos-demo/
├── Clusterfile          # 集群定义文件
├── manifests/           # Kubernetes 资源定义
│   └── demo-app.yaml    # 应用部署文件
└── images/              # 附加镜像（可选）
```

## 构建集群镜像的步骤

### 1. 构建应用镜像
```bash
# 已经执行：docker build -t demo-app:1.0 .
```

### 2. 推送应用镜像到仓库（如果需要）
```bash
# 为镜像打标签
docker tag demo-app:1.0 your-registry/demo-app:1.0

# 推送镜像
docker push your-registry/demo-app:1.0
```

### 3. 创建 Sealos 集群镜像
```bash
# 方法1：使用 sealos build 命令（如果支持）
# sealos build -f Clusterfile -t your-registry/demo-cluster:1.0 .

# 方法2：直接使用集群定义
# sealos run -f Clusterfile
```

### 4. 运行集群
```bash
# 使用 Sealos 部署集群
sealos run swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/kubernetes:v1.28.0 \
           swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/calico:v3.26.5 \
           --with-images demo-app:1.0
```

## 在 WSL 环境中使用（推荐方式）

要在中国网络环境下部署包含自定义应用的集群，推荐步骤如下：

1. 确保 Docker 运行正常
2. 使用我们的脚本绕过 containerd 检查
3. 部署集群并应用自定义应用

### 完整部署命令示例：
```bash
# 1. 首先备份 containerd 文件
sudo mv /usr/bin/containerd /usr/bin/containerd.bak
sudo mv /usr/bin/ctr /usr/bin/ctr.bak
sudo mv /usr/bin/containerd-shim-runc-v2 /usr/bin/containerd-shim-runc-v2.bak
sudo systemctl restart docker

# 2. 部署基础集群
sealos run swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/kubernetes:v1.28.0 \
           swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/labring/calico:v3.26.5 --single

# 3. 部署应用
kubectl apply -f /opt/github/SQLBot/sealos-demo/manifests/demo-app.yaml

# 4. 恢复 containerd 文件
sudo mv /usr/bin/containerd.bak /usr/bin/containerd
sudo mv /usr/bin/ctr.bak /usr/bin/ctr
sudo mv /usr/bin/containerd-shim-runc-v2.bak /usr/bin/containerd-shim-runc-v2
sudo systemctl restart docker
```

### 简化版本（使用我们的脚本）
```bash
# 运行我们的脚本来部署基础集群（已测试可用）
bash /opt/github/SQLBot/install_sealos_wsl_final.sh

# 然后部署应用
kubectl apply -f /opt/github/SQLBot/sealos-demo/manifests/demo-app.yaml
```