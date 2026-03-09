# SQLBot Helm Chart

在 Kubernetes 上部署 SQLBot（All-in-One：后端 + 前端 + g2-ssr + 内嵌 PostgreSQL）。

## 前置条件

- Kubernetes 1.19+
- Helm 3
- 可拉取的 SQLBot 镜像（如 `dataease/sqlbot:latest` 或自有仓库）

## 安装

```bash
# 使用默认 values
helm install sqlbot ./deploy/helm/sqlbot --namespace sqlbot --create-namespace

# 指定镜像
helm install sqlbot ./deploy/helm/sqlbot --namespace sqlbot --create-namespace \
  --set image.repository=registry.cn-qingdao.aliyuncs.com/dataease/sqlbot \
  --set image.tag=v1.0.0

# 使用自定义 values 文件
helm install sqlbot ./deploy/helm/sqlbot -f my-values.yaml --namespace sqlbot --create-namespace
```

## 升级

```bash
helm upgrade sqlbot ./deploy/helm/sqlbot --namespace sqlbot -f my-values.yaml
```

## 主要 values 说明

| 项 | 说明 | 默认 |
|----|------|------|
| `image.repository` | 镜像地址（可含 registry） | `dataease/sqlbot` |
| `image.tag` | 镜像 tag | `latest` |
| `image.pullPolicy` | 拉取策略 | `IfNotPresent` |
| `replicaCount` | 副本数（内嵌 DB 时建议保持 1） | `1` |
| `service.apiPort` / `service.mcpPort` | API 与 MCP 端口 | `8000` / `8001` |
| `persistence.enabled` | 是否启用持久化 | `true` |
| `persistence.storageClass` | StorageClass（空则用默认） | `""` |
| `persistence.postgresql.size` | PostgreSQL 数据盘大小 | `10Gi` |
| `persistence.data.size` | 应用数据（excel/file）大小 | `5Gi` |
| `config.*` | 应用非敏感配置（见 values.yaml） | 见文件 |
| `secret.POSTGRES_PASSWORD` | 数据库密码（生产请修改） | `Password123@pg` |
| `secret.SECRET_KEY` | 应用密钥（生产必须设置） | 未设置时使用占位符，需在 values 中设置 |
| `existingSecret` | 使用已有 Secret 名称（含 POSTGRES_PASSWORD、SECRET_KEY） | `""` |
| `ingress.enabled` | 是否创建 Ingress | `false` |
| `ingress.host` | Ingress 主机名 | `sqlbot.example.com` |
| `resources` | CPU/内存 requests 与 limits | 见 values.yaml |

## 持久化

启用 `persistence.enabled` 后会创建 4 个 PVC：

- `*-postgresql`：PostgreSQL 数据（`/var/lib/postgresql/data`）
- `*-data`：应用数据（`/opt/sqlbot/data`，含 excel、file）
- `*-images`：图片资源（`/opt/sqlbot/images`）
- `*-logs`：日志（`/opt/sqlbot/app/logs`）

可按需在 values 中调整 `persistence.*.size` 和 `persistence.storageClass`。

## Ingress

开启 Ingress 并配置 host/TLS：

```yaml
ingress:
  enabled: true
  className: nginx
  host: sqlbot.yourdomain.com
  tls:
    - secretName: sqlbot-tls
      hosts:
        - sqlbot.yourdomain.com
```

## 使用已有 Secret

若敏感信息由外部系统管理，可指向已有 Secret（需包含 key：`POSTGRES_PASSWORD`、`SECRET_KEY`）：

```yaml
existingSecret: my-sqlbot-secret
```

此时 Chart 不会创建 Secret 资源。

## 与构建脚本配合

项目根目录 `build/build-k8s.sh` 支持构建镜像后执行 Helm 部署，例如：

```bash
cd build
REGISTRY=registry.cn-qingdao.aliyuncs.com IMAGE_TAG=v1.0.0 \
  ./build-k8s.sh --push --helm-install
```

会使用当前构建的镜像执行 `helm upgrade --install`，并自动设置 `image.repository` 与 `image.tag`。
