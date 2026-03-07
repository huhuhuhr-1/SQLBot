# 常见工作流

## 工作流 1：元数据初始化

**目标**：将数据库元数据导入到 meta-repository

```bash
skill_session_init meta-ops init-metadata "初始化元数据"

# 1. 探查数据库（生成 JSON 格式）
java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:17082/mydb \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o full --schema public \
  --format json \
  --output "$(skill_session_report_path metadata.json)" 2>&1 | \
  tee "$(skill_session_log_path discovery.log)"

# 2. 导入到 meta-repository
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar \
  import from-file "$(skill_session_report_path metadata.json)" 2>&1 | \
  tee "$(skill_session_log_path import.log)"

# 3. 验证导入
java -jar .claude/skills/meta-ops/scripts/meta-cli.jar datasource list \
  > "$(skill_session_report_path datasources.md)"

skill_session_finish "元数据初始化完成"
```

## 工作流 2：数据集成准备

**目标**：探查源表和目标表结构，为数据同步做准备

```bash
skill_session_init meta-ops data-integration-prep "数据集成准备"

# 1. 探查源表
java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:17082/source_db \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o describe --schema public --table users \
  --format json \
  --output "$(skill_session_report_path source_table.json)"

# 2. 探查目标表
java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:17082/target_db \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o describe --schema public --table users \
  --format json \
  --output "$(skill_session_report_path target_table.json)"

# 3. 生成同步配置（使用 data-integration 技能）
# ...

skill_session_finish "探查完成，可生成同步配置"
```

## 工作流 3：数据库结构分析

**目标**：生成完整的数据库结构分析报告

```bash
skill_session_init meta-ops analyze-db "数据库结构分析"

# 1. 列出所有 schema
java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:17082/mydb \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o schemas \
  --output "$(skill_session_report_path schemas.md)"

# 2. 列出所有表
java -jar .claude/skills/meta-ops/scripts/meta-discovery.jar \
  -u postgres -p postgres \
  -j jdbc:postgresql://localhost:17082/mydb \
  --driver .claude/skills/database-drivers/drivers/postgresql-42.3.8.jar \
  --driverClass org.postgresql.Driver \
  -o tables --schema public \
  --output "$(skill_session_report_path tables.md)"

# 3. 生成表结构报告（循环处理所有表）
# ...

skill_session_finish "数据库分析完成"
```