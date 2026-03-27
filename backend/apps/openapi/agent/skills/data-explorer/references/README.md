# Data Explorer Skill v2.0.1 - 使用指南

## 快速开始

### 1. 初始化

```bash
cd /home/huhuhuhr/code/SQLBot/.claude/skills/data-explorer
bash scripts/run.sh init 1 http://localhost:8000/api/v1 <your_token>
```

### 2. 同步元数据

```bash
# 同步权限
bash scripts/run.sh pull-permissions 1

# 同步索引 (L1/L2)
bash scripts/run.sh pull-index 1 2

# 同步语义层
bash scripts/run.sh pull-semantic 1 2

# 同步单表 (L3)
bash scripts/run.sh pull-table 1 2 ci_builds
```

### 3. 执行查询

```bash
bash scripts/run.sh exec 1 2 "SELECT * FROM ci_builds LIMIT 10" result.csv
```

## 命令参考

| 命令 | 参数 | 说明 |
|------|------|------|
| `init` | user_id, url, token | 初始化用户空间 |
| `check` | user_id, db_id | 检查元数据状态 |
| `pull-permissions` | user_id | 同步权限 |
| `pull-index` | user_id, db_id | 同步 L1/L2 索引 |
| `pull-table` | user_id, db_id, table | 同步单表详情 |
| `pull-tables` | user_id, db_id | 同步全表详情 |
| `pull-semantic` | user_id, db_id | 同步术语 |
| `pull-relations` | user_id, db_id | 同步关系图 |
| `exec` | user_id, db_id, sql, file | 执行查询 |

## 目录结构

```
~/.sqlbot/<uid>/
├── config.json
├── exports/
├── permissions/datasources.json
├── schema/<db_id>/
│   ├── index.json
│   ├── summary.json
│   └── tables/*.json
├── semantic/<db_id>/
│   └── terminologies.*
└── relations/<db_id>/
    └── table_relations.json
```

## 帮助

```bash
bash scripts/run.sh -h
```