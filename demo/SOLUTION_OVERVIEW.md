# SQLBot with Sealos 部署解决方案

## 方案概述

本方案提供了一个完整的 SQLBot 应用在 Kubernetes 上的部署解决方案，使用 Sealos 作为 Kubernetes 发行版。方案包含：

1. **WSL 兼容性处理** - 解决 Docker 与 Sealos 在 WSL 环境中的冲突
2. **完整的应用部署** - 包括 SQLBot 应用和 PostgreSQL 数据库
3. **数据持久化** - 通过 PVC 确保数据持久存储
4. **服务暴露** - 通过 NodePort 和 Ingress 暴露服务
5. **生产就绪配置** - 包含资源限制、健康检查等生产级配置

## 解决方案特点

- **一键部署** - 通过 Sealos 实现一键部署完整的 SQLBot 集群
- **WSL 支持** - 特别优化了在 WSL 环境中的部署流程
- **高可用性** - 基于生产级的 Kubernetes 和 Calico 网络插件
- **数据安全** - 使用 PVC 进行数据持久化，确保数据不丢失
- **网络访问** - 提供多种访问方式（NodePort、Ingress）

## 架构图

```
┌─────────────────────────────────────────┐
│           Sealos Kubernetes             │
│  ┌─────────────────────────────────┐    │
│  │        SQLBot Namespace         │    │
│  │                                 │    │
│  │  ┌──────────┐   ┌─────────────┐│    │
│  │  │  SQLBot   │   │  PostgreSQL ││    │
│  │  │  App      │   │  Database   ││    │
│  │  └──────────┘   └─────────────┘│    │
│  │        │              │         │    │
│  │        └──────────────┘         │    │
│  │              │                  │    │
│  │        ┌─────────────┐          │    │
│  │        │   PVCs      │          │    │
│  │        │(Persistent   │          │    │
│  │        │VolumeClaims) │          │    │
│  │        └─────────────┘          │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

## 部署步骤

### 1. 环境准备
- 确保安装了 Docker 和 Sealos
- 在 WSL 环境中可能需要特殊处理（参见 demo 目录中的脚本）

### 2. 构建镜像
```bash
cd /opt/github/SQLBot
docker build -t dataease/sqlbot:latest .
```

### 3. 部署集群
```bash
# 使用部署脚本
bash /opt/github/SQLBot/demo/sealos-build/deploy-sqlbot.sh new
```

### 4. 验证部署
```bash
bash /opt/github/SQLBot/demo/sealos-build/deploy-sqlbot.sh verify
```

## 访问应用

部署成功后，您可以通过以下方式访问 SQLBot：

1. **API 端点**: http://<node-ip>:30000
2. **UI 端点**: http://<node-ip>:30001  
3. **通过 Ingress**: http://sqlbot.local (需要配置 hosts 文件)

## 维护和管理

- **日志查看**: `kubectl logs -n sqlbot -l app=sqlbot`
- **进入容器**: `kubectl exec -n sqlbot -it deployment/sqlbot -- /bin/bash`
- **扩容**: `kubectl scale -n sqlbot deployment/sqlbot --replicas=2`
- **更新配置**: 修改 ConfigMap 后重启 Pod

## 故障排除

常见问题和解决方案:

1. **WSL 冲突**: 使用提供的脚本处理 Docker 和 Sealos 冲突
2. **镜像拉取失败**: 检查网络连接和镜像仓库访问权限
3. **资源不足**: 确保主机有足够 CPU、内存和磁盘空间
4. **服务无法访问**: 检查防火墙设置和 NodePort 可用性

## 扩展性

该方案设计为可扩展:
- 可以轻松添加更多微服务
- 支持水平扩展（增加副本数）
- 可以集成外部存储、监控和日志系统
- 支持多环境部署（开发、测试、生产）