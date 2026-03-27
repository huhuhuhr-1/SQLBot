# Data Explorer 实现指南

## 核心架构

### .sqlbot 缓存结构

```
~/.sqlbot/<uid>/
├── config.json                     # API 连接配置 (url + token)
├── exports/                        # SQL 查询导出的 CSV 文件
├── permissions/
│   └── datasources.json            # 用户可见的数据源列表
├── schema/<db_id>/
│   ├── index.json                  # L1: 完整 API 响应（包含 table_schema）
│   ├── summary.json                # L2: 表概要（M-Schema 格式的 DDL）
│   └── tables/<table_name>.json    # L3: 单表详情（字段、类型、注释、字典项）
├── semantic/<db_id>/
│   ├── terminologies.json          # 业务术语列表（word + description + synonyms）
│   └── terminologies_raw.txt       # 原始术语文本
└── relations/<db_id>/
    └── table_relations.json        # 表关系图（edges: source_table → target_table）
```

### 分层加载策略

| 层级 | 内容 | 加载方式 | 用途 |
|------|------|----------|------|
| L1 | 数据源索引 | `pull-index` → index.json | 了解有哪些表 |
| L2 | 表概要 (M-Schema) | `pull-index` → summary.json | 了解表结构和字段 |
| L3 | 单表 DDL + 注释 + 字典 | `pull-table` → tables/*.json | 精确建模 SQL |

### SQL 执行流程

1. Agent 根据 L2/L3 元数据编写 SQL
2. 调用 `run.sh exec <uid> <db_id> "<SQL>" result.csv`
3. 脚本调用 `/openapi/getDataByDbIdAndSqlCsv` 接口
4. 结果保存为 CSV 到 `exports/` 目录
5. Agent 读取 CSV 分析数据

### 安全约束

- SQL 执行端点只允许 SELECT/SHOW/DESCRIBE/EXPLAIN/WITH 语句
- 禁止 INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE 等 DML/DDL
- 每个用户的数据隔离在 `~/.sqlbot/<uid>/` 下

## 关键 API 端点

| 功能 | 方法 | 路径 |
|------|------|------|
| 登录 | POST | /openapi/getToken |
| 数据源列表 | GET | /openapi/getDataSourceList |
| Schema + 术语 | POST | /openapi/getDataSourceByIdOrName |
| 全部术语 | GET | /openapi/getAllTerminologiesByDataSource |
| 表关系 | POST | /table_relation/get/{ds_id} |
| SQL→CSV | POST | /openapi/getDataByDbIdAndSqlCsv |
| SQL→JSON | POST | /openapi/getDataByDbIdAndSql |
