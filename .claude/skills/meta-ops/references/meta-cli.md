# 工具 2：元数据管理 (meta-cli)

## 基本信息

**JAR 文件**：`.claude/skills/meta-ops/scripts/meta-cli.jar`

**前置条件**：meta-repository 服务运行（http://localhost:17080）

**用途**：数据源管理、元数据查询、批量导入。

## 语法

```bash
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar <command> [options]
```

## 功能模块

### 2.1 数据源管理

```bash
# 列出所有数据源
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar datasource list

# 查看数据源详情
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar datasource get <datasource-id>

# JSON 格式输出（便于脚本处理）
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar datasource list --output json
```

### 2.2 表管理

```bash
# 查看表详情
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar table get <table-id>

# 查看表字段
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar table columns <table-id>

# 查看数据源的所有表
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar datasource tables <datasource-id>
```

### 2.3 元数据导入

**从文件导入**：

```bash
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar import from-file <metadata.json>
```

**导入文件格式（JSON）**：

```json
{
  "datasourceName": "my_postgres",
  "datasourceType": "SOURCE",
  "jdbcUrl": "jdbc:postgresql://localhost:5432/mydb",
  "username": "user",
  "password": "pass",
  "host": "localhost",
  "port": 5432,
  "databaseName": "mydb",
  "tables": [
    {
      "tableName": "users",
      "tableType": "TABLE",
      "schemaName": "public",
      "rowCount": 1000,
      "columns": [
        {
          "columnName": "id",
          "typeName": "bigserial",
          "columnSize": 19,
          "nullable": false,
          "isPrimaryKey": true,
          "isAutoIncrement": true
        },
        {
          "columnName": "username",
          "typeName": "varchar",
          "columnSize": 100,
          "nullable": false,
          "isPrimaryKey": false
        },
        {
          "columnName": "email",
          "typeName": "varchar",
          "columnSize": 255,
          "nullable": true,
          "isPrimaryKey": false
        }
      ]
    }
  ]
}
```

## 使用示例

### 完整导入流程

```bash
skill_session_init meta-ops import-meta "导入元数据"

# 1. 探查数据库（生成 JSON 格式元数据）
java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:5432/mydb \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o full --format json \
  --output "$(skill_session_report_path metadata.json)"

# 2. 导入到 meta-repository
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar \
  import from-file "$(skill_session_report_path metadata.json)"

# 3. 验证导入
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar datasource list

skill_session_finish "元数据导入完成"
```

## 使用 skill-exec

```bash
# 查询数据源列表
.claude/skills/shared/bin/skill-exec \
  meta-ops query-datasource "查询所有数据源" -- \
  java -jar .claude/skills/meta-ops/scripts/meta-cli.jar \
    datasource list \
    --output "$REPORT_FILE"

# 导入元数据
.claude/skills/shared/bin/skill-exec \
  meta-ops import-meta "导入元数据" -- \
  java -jar .claude/skills/meta-ops/scripts/meta-cli.jar \
    import from-file metadata.json
```