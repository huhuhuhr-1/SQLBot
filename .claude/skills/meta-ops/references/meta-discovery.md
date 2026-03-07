# 工具 1：数据库结构探查 (meta-discovery)

## 基本信息

**JAR 文件**：`.claude/skills/meta-ops/scripts/meta-discovery.jar`

**用途**：探查数据库结构，列出 schema/表，查看表结构，提取字段/索引/约束。

## 语法

```bash
java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u <user> -p <password> -j <jdbc_url> \
  --driver <driver_jar> --driverClass <driver_class> \
  -o <operation> [--schema <schema>] [--table <table>] \
  [--format json|text|markdown] [--output <file>]
```

## 操作类型

| 操作         | 说明             | 常用参数                                | 输出        |
|------------|----------------|-------------------------------------|-----------|
| `test`     | 测试数据库连接        | 无                                   | 连接状态      |
| `schemas`  | 列出所有 schema    | 无                                   | schema 列表 |
| `tables`   | 列出指定 schema 的表 | `--schema <schema>`                 | 表名列表      |
| `describe` | 描述表结构          | `--schema <schema> --table <table>` | 字段详情      |
| `full`     | 完整探查（所有表和字段）   | `--schema <schema>`（可选）             | 完整元数据     |

## 数据库驱动配置

| 数据库        | JDBC URL                               | 驱动 JAR                                                                 | 驱动类                        |
|------------|----------------------------------------|------------------------------------------------------------------------|----------------------------|
| PostgreSQL | `jdbc:postgresql://host:port/database` | `.claude/skills/database-drivers/drivers/postgresql-42.3.8.jar`        | `org.postgresql.Driver`    |
| MySQL      | `jdbc:mysql://host:port/database`      | `.claude/skills/database-drivers/drivers/mysql-connector-j-8.0.28.jar` | `com.mysql.cj.jdbc.Driver` |
| Oracle     | `jdbc:oracle:thin:@host:1521:ORCL`     | `.claude/skills/database-drivers/drivers/ojdbc8.jar`                   | `oracle.jdbc.OracleDriver` |

## 使用示例

### 1. 测试连接

```bash
skill_session_init meta-ops test-conn "测试数据库连接"

java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:17082/metadata_db \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o test
```

### 2. 列出所有表

```bash
skill_session_init meta-ops list-tables "列出所有表"

java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:17082/metadata_db \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o tables --schema public \
  --output "$(skill_session_report_path tables.md)"
```

### 3. 查看表结构

```bash
skill_session_init meta-ops describe-table "查看 users 表结构"

java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:17082/metadata_db \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o describe --schema public --table users \
  --format markdown \
  --output "$(skill_session_report_path users_structure.md)"
```

### 4. 完整探查（JSON 格式）

```bash
skill_session_init meta-ops discovery-full "完整探查数据库"

java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:17082/metadata_db \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o full --schema public \
  --format json \
  --output "$(skill_session_report_path full_metadata.json)"

skill_session_finish "探查完成"
```

## 使用 skill-exec

```bash
# 测试连接
.claude/skills/shared/bin/skill-exec \
  meta-ops test-conn "测试 PostgreSQL 连接" -- \
  java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
    -u sqlbot -p sqlbot \
    -j jdbc:postgresql://localhost:8086/sqlbot \
    --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
    --driverClass org.postgresql.Driver \
    -o test

# 列出所有表
.claude/skills/shared/bin/skill-exec \
  meta-ops list-tables "列出所有表" -- \
  java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
    -u sqlbot -p sqlbot \
    -j jdbc:postgresql://localhost:8086/sqlbot \
    --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
    --driverClass org.postgresql.Driver \
    -o tables --schema public \
    --output "$REPORT_FILE"

# 查看表结构
.claude/skills/shared/bin/skill-exec \
  meta-ops describe-table "查看 users 表结构" -- \
  java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
    -u sqlbot -p sqlbot \
    -j jdbc:postgresql://localhost:8086/sqlbot \
    --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
    --driverClass org.postgresql.Driver \
    -o describe --schema public --table users \
    --format markdown \
    --output "$REPORT_FILE"
```