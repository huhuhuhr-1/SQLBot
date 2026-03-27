# Data Explorer Skill v2.0.1 - 技能完善说明

## 当前状态

### 已完成的功能

| 功能 | 文件 | 状态 |
|------|------|------|
| 初始化 | `scripts/sqlbot_utils.py::init_config` | ✅ |
| 索引同步 | `scripts/sqlbot_utils.py::pull_index` | ✅ |
| 元数据检查 | `scripts/sqlbot_utils.py::check_metadata` | ✅ |
| 权限同步 | `scripts/sqlbot_utils.py::pull_permissions` | ✅ |
| 语义层同步 | `scripts/sqlbot_utils.py::pull_semantic` | ✅ |
| 全量术语同步 | `scripts/sqlbot_utils.py::pull_terminologies_all` | ✅ |
| 关系图同步 | `scripts/sqlbot_utils.py::pull_relations` | ✅ |
| 单表同步 | `scripts/sqlbot_utils.py::pull_table` | ✅ |
| 全表同步 | `scripts/sqlbot_utils.py::pull_tables` | ✅ |
| SQL 执行 | `scripts/sqlbot_utils.py::exec_sql` | ✅ |
| 公共知识同步 | `scripts/sqlbot_utils.py::pull_knowledge_common` | ✅ |

### 目录结构

```
~/.sqlbot/
└── <uid>/
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

## 渐进式加载层级

| 层级 | 说明 | 文件大小 | 命令 |
|------|------|----------|------|
| L0 | 用户配置 | ~200B | `init` |
| L1 | 库索引 | ~100B | `pull-index` |
| L2 | 表概要 | ~10KB | `pull-index` |
| L3 | 单表详情 | ~2KB/表 | `pull-table` |
| L3-All | 全表详情 | ~2MB | `pull-tables` |
| Semantic | 术语 | ~5KB | `pull-semantic` |
| Relations | 关系图 | ~2KB | `pull-relations` |

## 典型工作流

```bash
# 1. 初始化 (一次性)
bash scripts/run.sh init 1 http://localhost:8000/api/v1 <token>

# 2. 同步权限
bash scripts/run.sh pull-permissions 1

# 3. 同步 L1/L2 索引
bash scripts/run.sh pull-index 1 2

# 4. 检查元数据状态
bash scripts/run.sh check 1 2

# 5. 同步语义层
bash scripts/run.sh pull-semantic 1 2

# 6. 同步关系图
bash scripts/run.sh pull-relations 1 2

# 7. 按需同步单表
bash scripts/run.sh pull-table 1 2 ci_builds
bash scripts/run.sh pull-table 1 2 ci_pipelines

# 8. 执行查询
bash scripts/run.sh exec 1 2 "SELECT * FROM ci_builds LIMIT 100" result.csv
```

## API 依赖

| API | 用途 | 端点 |
|-----|------|------|
| 获取数据源 | pull-index | POST /openapi/getDataSourceByIdOrName |
| 获取数据源列表 | pull-permissions | GET /openapi/getDataSourceList |
| 获取全量术语 | pull-terminologies-all | GET /openapi/getAllTerminologiesByDataSource |
| 获取表关系 | pull-relations | GET /table_relation/get/{dbid} |
| 执行 SQL | exec_sql | POST /openapi/getDataByDbIdAndSqlCsv |

## 元数据格式

### index.json

```json
{
  "id": 2,
  "name": "数据接入调度"
}
```

### schema/summary.json

```json
[
  {"table": "public.ci_builds", "comment": "CI 构建记录表"},
  {"table": "public.ci_pipelines", "comment": "CI 流水线表"}
]
```

### schema/tables/<table_name>.json

```json
{
  "table": "public.ci_builds",
  "ddl": "# Table: public.ci_builds\n[\n(finished_at:timestamp),\n(status:character varying),\n...\n]"
}
```

### semantic/terminologies.txt

```text
CI 构建 (Build，编译任务)
  代码提交后自动触发的编译、测试、打包流程

流水线 (Pipeline)
  由多个 Stage 组成的自动化流程定义
```

## Token 优化

- **紧凑 JSON**: 使用 `separators=(',', ':')` 减少空格
- **按需加载**: 仅同步需要的表，避免全量拉取
- **本地缓存**: 使用 `full_table_schema.txt` 缓存，避免重复网络请求

## 错误处理

| 错误 | 处理方式 |
|------|----------|
| 网络失败 | 打印错误信息，退出码 1 |
| 元数据缺失 | check 命令返回失败，提示同步 |
| SQL 执行失败 | 打印 API 返回的错误详情 |
| 表不存在 | pull_table 输出警告，继续下一表 |

## 下一步优化建议

1. **新增 API 支持**:
   - `POST /datasource/getDDL/{ds_id}/{table_name}` - 获取 DDL
   - `POST /datasource/getConstraints/{ds_id}/{table_name}` - 获取主键/外键
   - `POST /datasource/getFieldEnums/{ds_id}/{table_name}/{field_name}` - 获取枚举值
   - `POST /datasource/getSamples/{ds_id}/{table_name}` - 获取采样数据

2. **格式优化**:
   - 支持紧凑 JSON 输出
   - 支持 JSONL 格式 (L1 索引)

3. **增量同步**:
   - 添加 `--force` 参数强制刷新
   - 添加 `--if-modified` 参数按需刷新

4. **测试用例**:
   - 完善 `evals/evals.json`
   - 添加端到端测试脚本

## 相关链接

- [SQLBot 主项目](../../../)
- [v2.0 重构设计](../../../.sqlbot/REFACTOR_PLAN.md)
- [后端 API 代码](../../../backend/apps/datasource/api/)