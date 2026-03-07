# 数据库 Docker 镜像拉取指南

## 使用华为云镜像源加速

**镜像源地址**: `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/`

### 使用方法

将 Docker Hub 官方镜像地址替换为华为云镜像地址：

```bash
# Docker Hub 官方格式
docker pull docker.io/library/postgres:latest

# 华为云镜像格式
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/library/postgres:latest
```

**简化写法**（docker.io 可省略）：
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:latest
```

---

## 14 个数据库镜像拉取命令

### 1. PostgreSQL
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:latest
# 或指定版本
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:16
```

**运行示例**：
```bash
docker run -d \
  --name postgres \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=yourpassword \
  -v postgres_data:/var/lib/postgresql/data \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:latest
```

### 2. MySQL
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mysql:8.4
# 或最新版本
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mysql:latest
```

**运行示例**：
```bash
docker run -d \
  --name mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=yourpassword \
  -v mysql_data:/var/lib/mysql \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mysql:8.4
```

### 3. Oracle Database

**注意**：Oracle 官方镜像不在 Docker Hub 上，需要从 Oracle 官方获取。

```bash
# Oracle 官方提供 GitHub 仓库构建镜像
# 参考文档：https://github.com/oracle/docker-images
git clone https://github.com/oracle/docker-images.git
cd docker-images/OracleDatabase/SingleInstance/dockerfiles

# 构建 Oracle 23c Free 镜像
./buildContainerImage.sh -v 23.4.0 -s -x
```

**运行示例**（构建后）：
```bash
docker run -d \
  --name oracledb \
  -p 1521:1521 \
  -e ORACLE_PWD=yourpassword \
  -v oracle_data:/opt/oracle/oradata \
  oracle/database:23c-free
```

### 4. SQL Server
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/mcr.microsoft.com/mssql/server:2025-latest
```

**运行示例**：
```bash
docker run -d \
  --name sqlserver \
  -p 1433:1433 \
  -e ACCEPT_EULA=Y \
  -e SA_PASSWORD=YourStrong@Passw0rd \
  -v sqlserver_data:/var/opt/mssql \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/mcr.microsoft.com/mssql/server:2025-latest
```

### 5. MariaDB
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mariadb:latest
```

**运行示例**：
```bash
docker run -d \
  --name mariadb \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=yourpassword \
  -v mariadb_data:/var/lib/mysql \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mariadb:latest
```

### 6. MongoDB
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mongo:latest
```

**运行示例**：
```bash
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=yourpassword \
  -v mongodb_data:/data/db \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mongo:latest
```

### 7. H2 Database
```bash
# H2 没有官方镜像，使用社区维护的镜像
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/oscarfonts/h2:latest
```

**运行示例**：
```bash
docker run -d \
  --name h2 \
  -p 9092:9092 \
  -p 8082:8082 \
  -v h2_data:/opt/h2-data \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/oscarfonts/h2:latest
```

### 8. IBM DB2
```bash
# DB2 已迁移到 icr.io
docker pull icr.io/db2_community/db2:latest
# 或尝试华为云镜像（如果有同步）
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/ibmcom/db2:latest
```

**运行示例**：
```bash
docker run -d \
  --name db2 \
  -p 50000:50000 \
  -e DB2INST1_PASSWORD=yourpassword \
  -e LICENSE=accept \
  -v db2_data:/database \
  icr.io/db2_community/db2:latest
```

### 9. OceanBase
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/oceanbase/oceanbase-ce:latest
```

**运行示例**：
```bash
docker run -d \
  --name oceanbase \
  -p 2881:2881 \
  -p 2882:2882 \
  -e MODE=mini \
  -v oceanbase_data:/root/ob \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/oceanbase/oceanbase-ce:latest
```

### 10. ClickHouse
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/clickhouse/clickhouse-server:latest
```

**运行示例**：
```bash
docker run -d \
  --name clickhouse \
  -p 8123:8123 \
  -p 9000:9000 \
  -v clickhouse_data:/var/lib/clickhouse \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/clickhouse/clickhouse-server:latest
```

### 11. Apache Hive

**注意**：Hive 没有官方独立镜像，通常作为大数据平台的一部分。

**选项1：使用 Apache Linkis（包含 Hive）**
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/apache/linkis:latest
```

**选项2：使用社区 Hive 镜像**
```bash
# 需要先搜索可用的 Hive 镜像
docker search hive
# 例如：
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/bde2020/hive:latest
```

**注意**：Hive 通常需要 Hadoop、Metastore 等依赖，建议使用 docker-compose 部署。

### 12. 达梦数据库 (DM)

**注意**：达梦数据库不在 Docker Hub 上，需要从达梦官网获取。

**选项1：使用社区镜像**
```bash
# 可能有第三方镜像，搜索可用镜像
docker search dmdb
```

**选项2：从达梦官网获取**
- 访问达梦官网下载 Docker 镜像
- 或参考达梦安装文档手动构建

### 13. 人大金仓 (KingbaseES)

**选项1：使用官方文档中的方法**
```bash
# 从人大金仓官网下载镜像
# 参考：https://help.kingbase.com.cn/v8/install-updata/install-docker/index.html
docker load -i kingbase.tar
```

**选项2：使用 Docker Hub 社区镜像**
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/huzhihui/kingbase:latest
```

**运行示例**：
```bash
docker run -d \
  --name kingbase \
  -p 54321:54321 \
  -v kingbase_data:/home/kingbase/data \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/huzhihui/kingbase:latest
```

### 14. openGauss / GaussDB
```bash
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/opengauss/opengauss:latest
# 或轻量级版本
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/enmotech/opengauss-lite:latest
```

**运行示例**：
```bash
docker run -d \
  --name opengauss \
  -p 5432:5432 \
  -e GS_PASSWORD=YourPassword@123 \
  -v opengauss_data:/var/lib/opengauss \
  swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/opengauss/opengauss:latest
```

---

## 快速参考表

| 数据库 | 镜像路径 | 默认端口 | 状态 |
|--------|---------|---------|------|
| PostgreSQL | `postgres` | 5432 | ✅ 官方 |
| MySQL | `mysql` | 3306 | ✅ 官方 |
| Oracle | 需从 Oracle 官方获取 | 1521 | ⚠️ 需手动获取 |
| SQL Server | `mcr.microsoft.com/mssql/server` | 1433 | ✅ 官方 |
| MariaDB | `mariadb` | 3306 | ✅ 官方 |
| MongoDB | `mongo` | 27017 | ✅ 官方 |
| H2 Database | `oscarfonts/h2` | 9092, 8082 | ⚠️ 社区 |
| IBM DB2 | `ibmcom/db2` 或 `icr.io/db2_community/db2` | 50000 | ✅ 官方 |
| OceanBase | `oceanbase/oceanbase-ce` | 2881, 2882 | ✅ 官方 |
| ClickHouse | `clickhouse/clickhouse-server` | 8123, 9000 | ✅ 官方 |
| Apache Hive | 需使用大数据平台镜像 | 多端口 | ⚠️ 需组合部署 |
| 达梦数据库 | 需从达梦官网获取 | 5236 | ⚠️ 需手动获取 |
| 人大金仓 | `huzhihui/kingbase` | 54321 | ⚠️ 社区 |
| openGauss | `opengauss/opengauss` | 5432 | ✅ 官方 |

---

## Docker Compose 示例

### PostgreSQL 示例
```yaml
version: '3.8'
services:
  postgres:
    image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:16
    container_name: postgres
    environment:
      POSTGRES_PASSWORD: yourpassword
      POSTGRES_DB: mydb
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

### MySQL 示例
```yaml
version: '3.8'
services:
  mysql:
    image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mysql:8.4
    container_name: mysql
    environment:
      MYSQL_ROOT_PASSWORD: yourpassword
      MYSQL_DATABASE: mydb
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    restart: unless-stopped

volumes:
  mysql_data:
```

### 多数据库组合示例
```yaml
version: '3.8'
services:
  postgres:
    image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:16
    container_name: postgres
    environment:
      POSTGRES_PASSWORD: postgres123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mysql:
    image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/mysql:8.4
    container_name: mysql
    environment:
      MYSQL_ROOT_PASSWORD: mysql123
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql

  clickhouse:
    image: swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/clickhouse/clickhouse-server:latest
    container_name: clickhouse
    ports:
      - "8123:8123"
      - "9000:9000"
    volumes:
      - clickhouse_data:/var/lib/clickhouse

volumes:
  postgres_data:
  mysql_data:
  clickhouse_data:
```

---

## 配置 Docker 镜像加速器（可选）

如果不想每次都输入完整的镜像地址，可以配置 Docker registry mirror：

### Linux 系统
编辑 `/etc/docker/daemon.json`：
```json
{
  "registry-mirrors": [
    "https://swr.cn-north-4.myhuaweicloud.com"
  ],
  "dns": ["8.8.8.8", "114.114.114.114"]
}
```

重启 Docker：
```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

### 验证配置
```bash
docker info | grep -A 10 "Registry Mirrors"
```

**注意**：配置 mirror 后，可以直接使用短名称：
```bash
# 配置后可直接使用
docker pull postgres:16

# 等同于
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:16
```

---

## 常见问题

### Q1: 镜像拉取失败？
**A**: 检查网络连接和镜像地址是否正确：
```bash
# 测试网络连通性
ping swr.cn-north-4.myhuaweicloud.com

# 查看详细信息
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:latest --debug
```

### Q2: 如何查看已下载的镜像？
**A**: 使用 docker images 命令：
```bash
docker images | grep -E "postgres|mysql|oracle"
```

### Q3: 容器启动失败？
**A**: 查看容器日志：
```bash
docker logs <container_name>
# 或
docker logs -f <container_name>  # 实时查看
```

### Q4: 数据持久化？
**A**: 使用 Docker volumes 或挂载宿主机目录：
```bash
# 使用 named volume
-v data_volume:/path/in/container

# 挂载宿主机目录
-v /host/path:/container/path
```

---

## 参考资源

- **华为云 SWR 文档**: https://support.huaweicloud.com/swr/
- **Docker Hub 官方**: https://hub.docker.com/
- **PostgreSQL Docker**: https://hub.docker.com/_/postgres
- **MySQL Docker**: https://hub.docker.com/_/mysql
- **Oracle Database GitHub**: https://github.com/oracle/docker-images
- **OceanBase Docker**: https://hub.docker.com/r/oceanbase/oceanbase-ce
- **ClickHouse Docker**: https://hub.docker.com/r/clickhouse/clickhouse-server
- **openGauss 官方文档**: https://docs.opengauss.org/zh/
- **人大金仓 Docker 部署手册**: https://help.kingbase.com.cn/v8/install-updata/install-docker/index.html

---

**文档版本**: v1.0
**最后更新**: 2026-01-09
**维护者**: AI 数据治理团队
