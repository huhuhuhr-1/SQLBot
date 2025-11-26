# Sealos WSL 部署脚本

`install_sealos_wsl.sh` 脚本用于在 WSL 环境中部署 Sealos Kubernetes 集群，同时保持 Docker 服务正常运行。

## 问题背景

在 WSL (Ubuntu 22.04) 环境中，Docker 自带的 containerd 与 Sealos 冲突，导致 Sealos 无法正常部署 Kubernetes 集群。

## 解决方案

脚本通过以下步骤解决此问题：

1. **检测并备份** - 检测 Docker 是否运行，并临时重命名 containerd 二进制文件
2. **部署集群** - 使用 Sealos 部署 Kubernetes + Calico 集群
3. **恢复服务** - 无论成功或失败，都会恢复 containerd 文件并重启 Docker
4. **验证结果** - 检查集群状态和 Docker 功能

## 使用方法

```bash
bash install_sealos_wsl.sh
```

## 重要说明

- 如果部署过程中发生网络超时等错误，脚本会自动执行恢复程序
- 脚本的绕过检查机制工作正常，部署失败通常是由于镜像拉取的网络问题
- 成功部署需要稳定网络连接来下载所需镜像

## 验证命令

脚本执行完成后，会显示以下验证信息：
- `kubectl get node` - 显示节点状态
- `kubectl get pods -A | head` - 显示运行的 Pod
- `docker ps` - 显示 Docker 容器状态