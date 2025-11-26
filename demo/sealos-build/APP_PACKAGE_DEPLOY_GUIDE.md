# SQLBot 应用包部署指南

## 应用包内容
- `sqlbot-app.yaml` - Kubernetes 部署配置文件
- `Applicationfile` - Sealos 应用定义文件
- `package-info.yaml` - 包信息文件
- `README.md` - 使用说明

## 部署方法

### 方法1: 直接使用 kubectl (推荐)
```bash
# 应用 SQLBot 部署配置
kubectl apply -f sqlbot-app.yaml
```

### 方法2: 使用 Sealos 应用管理
```bash
# 如果有 Sealos 应用管理功能
sealos apply -f Applicationfile
```

## 验证部署
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
- **API 访问**: `http://<node-ip>:30000`
- **UI 访问**: `http://<node-ip>:30001`
- **Ingress 访问**: `http://sqlbot.local` (需要添加到 /etc/hosts)

## 升级应用
```bash
# 修改配置后重新应用
kubectl apply -f sqlbot-app.yaml

# 或者使用滚动更新
kubectl rollout restart deployment/sqlbot -n sqlbot
```

## 删除应用
```bash
# 删除整个命名空间（会删除所有相关资源）
kubectl delete namespace sqlbot

# 或者单独删除资源
kubectl delete -f sqlbot-app.yaml
```

## 注意事项
- 需要一个运行中的 Kubernetes 集群
- 集群需要支持持久化存储 (PV/PVC)
- 集群需要至少 4GB 内存和 2 个 CPU 核心
- 确保节点有足够磁盘空间用于数据存储
- SQLBot 内置 PostgreSQL，需要额外时间启动

## 故障排除
如果应用启动失败：
1. 检查 Pod 状态: `kubectl get pods -n sqlbot`
2. 查看日志: `kubectl logs -n sqlbot -l app=sqlbot`
3. 检查资源限制: `kubectl describe pod <pod-name> -n sqlbot`
4. 确认存储配置: `kubectl get pvc -n sqlbot`