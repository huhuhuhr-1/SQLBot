---
name: database-drivers
description: 统一的数据库驱动管理中心。当需要为 meta-discovery、data-integration、data-quality 或 data-security 技能提供数据库驱动时使用此技能。此技能集中管理所有数据库驱动 JAR 文件和元数据，避免重复存储和版本不一致。
---

# Database Drivers

## Overview

**统一的数据库驱动管理中心**，为 AI 数据治理平台的所有技能提供数据库驱动。

### 核心原则

- **单一数据源**：所有驱动只存储一份
- **统一版本管理**：避免版本不一致
- **按需引用**：其他技能从此处获取驱动

### 使用此驱动的技能

| 技能 | 用途 | 集成状态 | 引用方式 |
|------|------|----------|----------|
| **meta-discovery** | 元数据探查 | ✅ 完全集成 | `--driver` 参数指向本目录 |
| **data-integration** | DataX 数据同步 | ✅ 完全集成 | skill-packaging 从本目录收集到各插件 libs/ |
| **data-quality** | 数据质量检查 | ✅ 不需要 JDBC | 使用 Python psycopg2-binary |
| **data-security** | 敏感数据扫描 | ✅ 不需要 JDBC | 使用 Python psycopg2-binary |

## 驱动清单

当前支持的数据库驱动（14个）：

| 数据库 | 驱动类 | 版本 | 大小 | 状态 |
|--------|--------|------|------|------|
| PostgreSQL | `org.postgresql.Driver` | 42.3.8 | 1017K | ✅ 已下载 |
| MySQL | `com.mysql.jdbc.Driver` | 5.1.47 | 984K | ✅ 已下载 |
| Oracle | `oracle.jdbc.OracleDriver` | 23.26.0.0.0 | 7.3M | ✅ 已下载 |
| SQL Server | `com.microsoft.sqlserver.jdbc.SQLServerDriver` | 12.8.0 | 1.5M | ✅ 已下载 |
| MariaDB | `org.mariadb.jdbc.Driver` | 3.5.2 | 726K | ✅ 已下载 |
| MongoDB | `mongodb.jdbc.MongoDriver` | - | - | ⚠️ 无JDBC驱动 |
| H2 | `org.h2.Driver` | 2.4.240 | 2.6M | ✅ 已下载 |
| IBM DB2 | `com.ibm.db2.jcc.DB2Driver` | 12.1.3.0 | 6.4M | ✅ 已下载 |
| OceanBase | `com.oceanbase.jdbc.Driver` | 2.4.15 | 1.1M | ✅ 已下载 |
| ClickHouse | `com.clickhouse.jdbc.ClickHouseDriver` | 0.6.0 | 1.3M | ✅ 已下载 |
| Apache Hive | `org.apache.hive.jdbc.HiveDriver` | 4.2.0 | 168K | ✅ 已下载 |
| 达梦数据库 | `dm.jdbc.driver.DmDriver` | - | - | ⚠️ 需手动下载 |
| 人大金仓 | `com.kingbase8.Driver` | - | - | ⚠️ 需手动下载 |
| openGauss | `org.opengauss.Driver` | - | - | ⚠️ 需手动下载 |

**详细元数据**: 参见 `registry/drivers.json`
**下载脚本**: 参见 `scripts/download-drivers.sh`

## 驱动引用方式

### meta-discovery（元数据探查）

**命令行参数**（示例路径，实际使用时根据技能安装位置调整）：
```bash
java -jar meta-discovery.jar \
  --driver database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -u username -p password \
  -j jdbc:postgresql://localhost:5432/database
```

**配置文件**：
```json
{
  "driverPath": "database-drivers/drivers/postgresql-42.3.8.jar",
  "driverClass": "org.postgresql.Driver"
}
```

### data-integration（DataX 数据同步）

**构建时集成**（skill-packaging/package.xml 配置示例）：
```xml
<!-- 从 database-drivers 收集驱动到 DataX 插件 -->
<fileSet>
  <directory>database-drivers/drivers/</directory>
  <outputDirectory>datax/plugin/reader/rdbmsreader/libs</outputDirectory>
  <includes>
    <include>*.jar</include>
  </includes>
</fileSet>

<fileSet>
  <directory>database-drivers/drivers/</directory>
  <outputDirectory>datax/plugin/writer/rdbmswriter/libs</outputDirectory>
  <includes>
    <include>*.jar</include>
  </includes>
</fileSet>
```

### data-quality / data-security（Python 工具）

**环境变量**：
```python
import os
import jaydebeapi

# 从统一驱动目录加载（路径相对于技能根目录）
driver_path = "drivers/postgresql-42.3.8.jar"
conn = jaydebeapi.connect(
    "org.postgresql.Driver",
    "jdbc:postgresql://localhost:5432/database",
    ["username", "password"],
    driver_path
)
```

## 驱动注册表

驱动元数据存储在 `registry/drivers.json`：

```json
{
  "version": "1.0",
  "lastUpdated": "2026-01-09T16:30:00+08:00",
  "drivers": [
    {
      "name": "PostgreSQL",
      "databaseType": "postgresql",
      "jdbcUrlPattern": "jdbc:postgresql://.*",
      "driverClass": "org.postgresql.Driver",
      "driverJar": "drivers/postgresql-42.3.8.jar",
      "supported": true
    },
    {
      "name": "MySQL",
      "databaseType": "mysql",
      "jdbcUrlPattern": "jdbc:mysql://.*",
      "driverClass": "com.mysql.jdbc.Driver",
      "driverJar": "drivers/mysql-connector-java-5.1.47.jar",
      "supported": true
    }
  ]
}
```

## 维护指南

### 添加新数据库驱动

1. **下载驱动 JAR**：
   ```bash
   cd drivers/
   # 方式1：从 Maven Central 下载
   mvn dependency:get -Dartifact=org.oracle:ojdbc11:21.1.0.0

   # 方式2：手动下载后复制
   cp /path/to/ojdbc11.jar drivers/
   ```

2. **更新注册表**：编辑 `registry/drivers.json` 添加新驱动条目

3. **测试驱动**：
   ```bash
   # 使用 meta-discovery 测试连接
   java -jar meta-discovery.jar \
     --driver drivers/ojdbc11-21.1.0.0.jar \
     --driverClass oracle.jdbc.OracleDriver \
     -j jdbc:oracle:thin://localhost:1521:XE \
     -u user -p pass -o describe --table test_table
   ```

### 升级驱动版本

1. 备份旧版本（可选）：`mv drivers/postgresql-42.3.8.jar drivers/postgresql-42.3.8.jar.bak`
2. 下载新版本到 `drivers/` 目录
3. 更新 `registry/drivers.json` 中的版本号
4. 重新构建技能包（如果需要）

## 架构优势

### 改进前（驱动分散）
```
各技能分别维护驱动副本：
- meta-discovery: postgresql-42.3.8.jar (1017K)
- datax rdbmsreader: postgresql-42.3.8.jar (1017K)
- datax rdbmswriter: postgresql-42.3.8.jar (1017K)

总计：3 份副本，3MB 浪费
```

### 改进后（统一管理）
```
database-drivers/drivers/postgresql-42.3.8.jar (1017K)
├── meta-discovery → 引用
├── datax rdbmsreader → 构建时复制
└── datax rdbmswriter → 构建时复制

总计：1 份副本，节省空间
```

## 故障排查

### Q: meta-discovery 找不到驱动？
**A**: 检查 `--driver` 参数路径是否正确：
```bash
ls -lh drivers/postgresql-42.3.8.jar
```

### Q: DataX 报错 "ClassNotFoundException"？
**A**: 确认 skill-packaging/package.xml 正确配置了驱动收集规则

### Q: 如何验证驱动可用性？
**A**: 使用 meta-discovery 测试连接：
```bash
java -jar meta-discovery.jar \
  --driver drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -j jdbc:postgresql://localhost:5432/test \
  -u test -p test -o describe --table sys_user
```

## Docker 数据库部署

本技能提供了完整的 Docker 部署指南，方便您快速部署各种数据库进行测试和开发。

### 快速开始

**方式1：使用批量拉取脚本**（推荐）
```bash
# 拉取所有可用的数据库镜像（使用华为云镜像源加速）
cd .claude/skills/database-drivers
bash scripts/pull-docker-images.sh
```

**方式2：单独拉取镜像**
```bash
# 拉取特定数据库镜像（使用华为云镜像源）
docker pull swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:16

# 拉取后添加简短 tag
docker tag swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:16 postgres:16
docker rmi swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/postgres:16
```

### 常用数据库 Docker 命令

**PostgreSQL**:
```bash
docker run -d \
  --name postgres \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=yourpassword \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:16
```

**MySQL**:
```bash
docker run -d \
  --name mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=yourpassword \
  -v mysql_data:/var/lib/mysql \
  mysql:8.4
```

**Oracle Database**:
```bash
# Oracle 需要从官方 GitHub 仓库构建
git clone https://github.com/oracle/docker-images.git
cd docker-images/OracleDatabase/SingleInstance/dockerfiles
./buildContainerImage.sh -v 23.4.0 -s -x

# 运行
docker run -d \
  --name oracledb \
  -p 1521:1521 \
  -e ORACLE_PWD=yourpassword \
  oracle/database:23c-free
```

**SQL Server**:
```bash
docker run -d \
  --name sqlserver \
  -p 1433:1433 \
  -e ACCEPT_EULA=Y \
  -e SA_PASSWORD=YourStrong@Passw0rd \
  mcr.microsoft.com/mssql/server:2025-latest
```

**ClickHouse**:
```bash
docker run -d \
  --name clickhouse \
  -p 8123:8123 \
  -p 9000:9000 \
  -v clickhouse_data:/var/lib/clickhouse \
  clickhouse/clickhouse-server:latest
```

**openGauss**:
```bash
docker run -d \
  --name opengauss \
  -p 5432:5432 \
  -e GS_PASSWORD=YourPassword@123 \
  -v opengauss_data:/var/lib/opengauss \
  opengauss/opengauss:latest
```

### 完整部署指南

**详细文档**: 参见 [docs/docker-pull-guide.md](docs/docker-pull-guide.md)

该文档包含：
- 14个数据库的完整拉取命令
- 华为云镜像源使用指南
- Docker Compose 配置示例
- 多数据库组合部署方案
- 常见问题排查

### 镜像源说明

**华为云容器镜像服务 (SWR)**: `swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/`

优势：
- 国内访问速度快
- 稳定可靠
- 与 Docker Hub 保持同步

配置 Docker 镜像加速器（可选）：
```bash
# 编辑 /etc/docker/daemon.json
{
  "registry-mirrors": [
    "https://swr.cn-north-4.myhuaweicloud.com"
  ]
}

# 重启 Docker
sudo systemctl restart docker
```

## 相关技能

- **meta-discovery**: 数据库元数据探查工具
- **data-integration**: DataX ETL 数据同步工具
- **data-quality**: 数据质量检查工具
- **data-security**: 敏感数据扫描和脱敏工具
