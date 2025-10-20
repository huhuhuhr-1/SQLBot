# Sealos 打包方式详解

## 两种打包概念

### 1. 应用镜像打包 (Application Image)
- **目的**：只打包应用程序本身
- **内容**：只有应用容器和部署配置
- **适用场景**：已有 Kubernetes 集群，只需部署应用
- **文件**：`Applicationfile` + `sqlbot-app.yaml`
- **部署命令**：
  ```bash
  kubectl apply -f sqlbot-app.yaml
  ```

### 2. 集群镜像打包 (Cluster Image) 
- **目的**：打包完整的运行环境
- **内容**：Kubernetes 集群 + 应用程序
- **适用场景**：从零开始创建新的集群环境
- **文件**：`Clusterfile` + 所有依赖
- **部署命令**：
  ```bash
  sealos run kubernetes-image calico-image --with-images your-app:latest
  ```

## SQLBot 打包方案

### 方案1：纯应用打包（推荐用于已有集群）

目录结构：
```
sealos-build/
├── Applicationfile          # 应用定义文件
├── sqlbot-app.yaml          # 应用部署配置
└── sqlbot:latest            # Docker 应用镜像
```

部署到现有集群：
```bash
# 方式1: 直接使用 kubectl
kubectl apply -f sqlbot-app.yaml

# 方式2: 使用部署脚本
bash deploy-sqlbot.sh app
```

### 方案2：完整集群打包

目录结构：
```
sealos-build/
├── Clusterfile              # 集群定义文件
├── sqlbot-k8s.yaml          # 应用部署配置（旧版）
├── sqlbot-app.yaml          # 应用部署配置（新版）
└── sqlbot:latest            # Docker 应用镜像
```

创建完整集群：
```bash
bash deploy-sqlbot.sh full
```

## 选择建议

- **如果您已有 Kubernetes 集群** → 使用应用打包方案
- **如果您需要完整部署环境** → 使用集群打包方案
- **如果您在 WSL 环境** → 使用集群打包方案（自动处理 Docker/Sealos 冲突）
- **如果您在生产环境** → 使用应用打包方案（更轻量、更安全）

## 关键区别

| 特性 | 应用打包 | 集群打包 |
|------|----------|----------|
| 部署复杂度 | 低 | 高 |
| 资源消耗 | 少 | 多 |
| 集群依赖 | 需要现有集群 | 无（自建） |
| 部署速度 | 快 | 慢 |
| 适用场景 | 生产环境 | 开发/测试环境 |

## 环境要求

### 应用打包
- 运行的 Kubernetes 集群
- kubectl 访问权限
- 足够的命名空间权限

### 集群打包
- Docker 运行环境
- Sealos 工具
- 足够的系统资源（4核CPU，8GB内存推荐）