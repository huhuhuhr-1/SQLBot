# SQLBot Sealos 镜像构建配置

## 镜像构建配置
- 基础镜像: registry.cn-qingdao.aliyuncs.com/dataease/sqlbot-base:latest
- 构建平台: linux/amd64
- 运行端口: 3000, 8000, 8001, 5432
- 健康检查: curl http://localhost:8000

## Sealos 集群配置
- Kubernetes版本: v1.28.0
- 网络插件: Calico v3.26.5
- 存储: 使用 PVC 进行数据持久化
- 服务类型: NodePort + Ingress

## 部署要求
- 最低资源: 2核CPU, 4GB内存
- 推荐资源: 4核CPU, 8GB内存
- 存储需求: 
  - Excel数据: 10GB
  - 文件数据: 10GB  
  - 图片数据: 10GB
  - 日志数据: 10GB
  - PostgreSQL数据: 20GB

## 环境变量
详见 sqlbot-k8s.yaml 中的 ConfigMap 定义

## 服务依赖
- PostgreSQL 17 with pgvector
- 依赖外部向量模型服务（已通过 volume 挂载）

## 网络配置
- Service 通过 NodePort 暴露 (30000, 30001)
- Ingress 配置域名: sqlbot.local
- 内部服务通信使用 Kubernetes Service DNS

## 持久化存储
- 所有数据通过 PVC 持久化
- 支持动态存储卷配置
- 数据备份和恢复策略需外部管理