# 智能映射（表关系推断）功能说明

## 概述

数据源表关系支持「智能推断」：先按规则（库内外键 + 命名约定）推断，再可选由 LLM 根据 schema 与术语补全关系，与生成 SQL 时使用的表关系一致，便于多表 JOIN。

## 行为

- **规则优先**
  - **Layer 1**：从数据库标准元数据读取真实外键（MySQL/Doris/StarRocks 用 `information_schema.KEY_COLUMN_USAGE`，Pg/KingBase 用 `table_constraints` + `key_column_usage` 等）。
  - **Layer 2**：按命名约定推断（如 `xxx_id` → 对应表的 `id`，支持单复数 s/es/ies）。
- **LLM 补全**（默认开启）
  - 使用与生成 SQL 相同的 **m-schema**（表名、字段名、字段类型、表/字段注释）及该数据源下的**术语**，调用默认 LLM 仅补充规则未覆盖的关系。
  - 输出格式：每行 `表名.字段名=引用表.引用字段`，与【Foreign keys】一致。
  - 规则结果优先，LLM 只追加不重复的边；LLM 调用失败时仅返回规则结果。

## API

- `POST /api/v1/table_relation/infer/{ds_id}`  
  - Body：`{ "table_ids": [可选], "use_llm": true }`  
  - 返回：边列表 `[{ "shape": "edge", "source": { "cell", "port" }, "target": { "cell", "port" } }, ...]`

## 涉及文件

- `backend/apps/datasource/api/table_relation.py`：推断逻辑（规则 + LLM）、FieldObj 入参修复。
- `backend/apps/db/db_fk.py`：从库中查询标准外键（MySQL/Pg/KingBase 等）。

## 修复

- 智能映射调用 `get_fields_by_table_id(session, t.id, FieldObj())` 时，`FieldObj` 必填字段 `fieldName` 未传导致校验失败，已改为 `FieldObj(fieldName=None)`。
