---
name: meta-ops
description: 数据探查、元数据管理、数据库管理。适用于数据库结构分析、元数据导入、DDL/DML操作、数据源管理。当用户需要查看表结构、列出数据库表、创建/修改表、导入元数据或管理数据源时使用此技能。
context: fork
---

# Meta-Ops 元数据操作

元数据探查、管理和数据库操作的统一工具，支持 PostgreSQL、MySQL、Oracle 等主流数据库。

## 场景触发规则

### 数据库探查

**触发关键词**：探查数据库、查看表结构、列出所有表、数据库有哪些表、分析数据库结构、查看字段信息、查看主键索引

→ 使用工具：**meta-discovery** (scripts/meta-discovery.jar)

→ 参考文档：**`references/meta-discovery.md`**

### 元数据管理

**触发关键词**：导入元数据、注册数据源、管理数据源、查询元数据、查看数据源

→ 使用工具：**meta-cli** (scripts/meta-cli.jar)

→ 参考文档：**`references/meta-cli.md`**

### 数据库操作

**触发关键词**：创建表、修改表、添加字段、插入数据、更新数据、删除数据、DDL、DML

→ 使用工具：**db-operations** (scripts/db-operations-tool.jar)

→ 参考文档：**`references/db-operations.md`**

### 数据集成准备

**触发关键词**：准备数据同步、生成同步配置、探查源表和目标表、比较表结构、数据同步准备

→ 参考流程：**`references/workflows.md`** 中的"数据集成准备"

### 遇到问题

**触发关键词**：连接失败、驱动错误、权限问题、ClassNotFoundException、permission denied

→ 参考文档：**`references/troubleshooting.md`**

## 执行规范

### 使用 skill-exec 统一入口

```bash
.claude/skills/shared/bin/skill-exec \
  meta-ops <action-type> "<description>" -- \
  <command>
```

详细用法：[../shared/SKILL-EXEC-GUIDE.md](../shared/SKILL-EXEC-GUIDE.md)

## 工具清单

| 工具             | JAR 文件                         | 功能            | 文档                                 |
|----------------|--------------------------------|---------------|------------------------------------|
| meta-discovery | scripts/meta-discovery.jar     | 测试连接、列出表、查看结构 | **`references/meta-discovery.md`** |
| meta-cli       | scripts/meta-cli.jar           | 数据源管理、元数据导入   | **`references/meta-cli.md`**       |
| db-operations  | scripts/db-operations-tool.jar | DDL/DML 操作    | **`references/db-operations.md`**  |

## 协作技能

- **database-drivers**：数据库驱动管理
- **data-integration**：数据同步
- **data-quality**：数据质量检查
- **data-security**：敏感数据扫描