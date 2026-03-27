# SQLBot 本地 K8s 部署（镜像 zf-sqlbot:latest）

使用本地镜像 `zf-sqlbot:latest` 在 Kubernetes 中运行 SQLBot。

## 前置条件

- 可用的 Kubernetes 集群（`kubectl get nodes` 能列出节点）
- 集群能使用镜像 `zf-sqlbot:latest`：
  - **单节点本机集群**：需把镜像导入集群（见下方「镜像准备」）
  - **多节点或远程集群**：建议将镜像推送到集群可访问的镜像仓库，并修改 `deployment.yaml` 中的 `image`

## 镜像准备（本机单节点集群）

若集群跑在本机且使用 containerd（如 Sealos），本机 Docker 的镜像不会自动可见，可二选一：

1. **推送到可访问的镜像仓库**  
   给镜像打 tag 并 push，然后在 deployment 里把 `image` 改成该仓库地址。

2. **导入到 containerd（本机节点）**  
   ```bash
   docker save zf-sqlbot:latest | sudo ctr -n k8s.io images import -
   ```

## 部署步骤

### 方式 A：使用 PVC（数据持久化）

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f pvc.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

需要集群有默认 StorageClass，否则 PVC 会一直 Pending。

### 方式 B：不使用 PVC（快速测试，数据不持久化）

不创建 PVC，改用 emptyDir 的 Deployment：

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment-no-pvc.yaml
kubectl apply -f service.yaml
```

## 访问服务

Service 类型为 NodePort：

- **API**：`http://<节点IP>:30080`
- **MCP**：`<节点IP>:30081`

本机单节点可用：

- `http://localhost:30080`
- `localhost:30081`

## 常用命令

```bash
# 查看 Pod
kubectl get pods -n sqlbot -o wide

# 查看日志
kubectl logs -f deployment/sqlbot -n sqlbot

# 删除部署
kubectl delete -f service.yaml -f deployment.yaml -f pvc.yaml -f secret.yaml -f configmap.yaml -f namespace.yaml
# 若用的是无 PVC 版本：
kubectl delete -f service.yaml -f deployment-no-pvc.yaml -f secret.yaml -f configmap.yaml -f namespace.yaml
```

## 当前环境说明

- **kubectl / kubelet / kubeadm / sealos** 已安装。
- **当前 kubeconfig** 指向 `apiserver.cluster.local:6443`（解析为 192.168.1.18），若该机器未启动或网络不通，`kubectl get nodes` 会超时。
- 若要用 **Sealos 单节点** 在本机起集群，需保证本机 SSH 可用，并指定 master 为本机 IP，例如：  
  `sealos run labring/kubernetes:v1.24.0 --masters $(hostname -I | awk '{print $1}')`  
  集群起来后，再按上述步骤部署，并按要求准备 `zf-sqlbot:latest` 镜像。
