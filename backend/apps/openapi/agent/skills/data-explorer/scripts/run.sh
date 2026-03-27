#!/usr/bin/env bash
# data-explorer skill — SQLBot API 客户端脚本
# 用法: bash scripts/run.sh <command> [args...]
set -euo pipefail

SQLBOT_HOME="${HOME}/.sqlbot"
CURL_OPTS="-s --connect-timeout 10 --max-time 60"

# ---------- helpers ----------
die()  { echo "ERROR: $*" >&2; exit 1; }
info() { echo "INFO: $*" >&2; }

ensure_user_dir() {
  local uid="$1"
  local udir="${SQLBOT_HOME}/${uid}"
  mkdir -p "${udir}"/{exports,schema,semantic,relations,permissions}
  echo "${udir}"
}

load_config() {
  local uid="$1"
  local cfg="${SQLBOT_HOME}/${uid}/config.json"
  [[ -f "$cfg" ]] || die "用户 ${uid} 未初始化。请先执行: run.sh login <uid> <username> <password>"
  cat "$cfg"
}

get_url()   { load_config "$1" | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])" 2>/dev/null; }
get_token() { load_config "$1" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null; }

api_call() {
  local uid="$1" method="$2" path="$3"
  shift 3
  local url
  url="$(get_url "$uid")${path}"
  local token
  token="$(get_token "$uid")"
  curl ${CURL_OPTS} -X "${method}" "${url}" \
    -H "Content-Type: application/json" \
    -H "X-SQLBOT-TOKEN: ${token}" \
    "$@"
}

# ---------- commands ----------

cmd_help() {
  cat <<'EOF'
data-explorer run.sh — SQLBot 数据探查技能脚本

命令:
  login <uid> <username> <password>    登录并初始化用户空间
  init  <uid> <url> <token>            手动指定 Token 初始化
  check <uid> [db_id]                  检查元数据状态
  pull-index <uid> <db_id>             同步数据源索引 (L1/L2)
  pull-table <uid> <db_id> <table>     同步单表详情 (L3)
  pull-tables <uid> <db_id>            同步全表详情
  pull-semantic <uid> <db_id>          同步术语口径
  pull-relations <uid> <db_id>         同步表关系图
  pull-permissions <uid>               同步权限
  exec <uid> <db_id> <sql> [file.csv]  执行 SQL 并导出 CSV
  list-ds <uid>                        列出可用数据源
  describe <uid> <db_id>               描述数据源 schema

目录结构:
  ~/.sqlbot/<uid>/
  ├── config.json              # url + token
  ├── exports/                 # SQL 导出的 CSV 文件
  ├── permissions/             # 权限信息
  ├── schema/<db_id>/
  │   ├── index.json           # L1: 库级索引
  │   ├── summary.json         # L2: 表概要
  │   └── tables/<table>.json  # L3: 单表 DDL + 注释 + 字典
  ├── semantic/<db_id>/
  │   └── terminologies.json   # 业务术语
  └── relations/<db_id>/
      └── table_relations.json # 表关系图
EOF
}

cmd_login() {
  local uid="$1" username="$2" password="$3"
  local url="${SQLBOT_URL:-http://localhost:8000/api/v1}"
  local udir
  udir="$(ensure_user_dir "$uid")"

  info "登录 ${url} (用户: ${username})..."
  local resp
  resp=$(curl ${CURL_OPTS} -X POST "${url}/openapi/getToken" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${username}\",\"password\":\"${password}\"}")

  local token
  token=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null)

  if [[ -z "$token" || "$token" == "None" ]]; then
    die "登录失败: ${resp}"
  fi

  python3 -c "
import json
cfg = {'url': '${url}', 'token': '${token}', 'uid': '${uid}', 'username': '${username}'}
with open('${udir}/config.json', 'w') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
"
  info "登录成功，Token 已保存到 ${udir}/config.json"
}

cmd_init() {
  local uid="$1" url="$2" token="$3"
  local udir
  udir="$(ensure_user_dir "$uid")"

  # 确保 token 有 bearer 前缀
  if [[ "$token" != bearer* ]]; then
    token="bearer ${token}"
  fi

  python3 -c "
import json
cfg = {'url': '${url}', 'token': '${token}', 'uid': '${uid}'}
with open('${udir}/config.json', 'w') as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
"
  info "初始化完成: ${udir}/config.json"
}

cmd_list_ds() {
  local uid="$1"
  info "获取数据源列表..."
  api_call "$uid" GET "/openapi/getDataSourceList" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list):
    for ds in data:
        print(f\"  [{ds.get('id','')}] {ds.get('name','')} ({ds.get('type','')})\")
elif isinstance(data, dict) and 'data' in data:
    for ds in data['data']:
        print(f\"  [{ds.get('id','')}] {ds.get('name','')} ({ds.get('type','')})\")
else:
    print(json.dumps(data, ensure_ascii=False, indent=2))
"
}

cmd_pull_index() {
  local uid="$1" db_id="$2"
  local udir="${SQLBOT_HOME}/${uid}"
  mkdir -p "${udir}/schema/${db_id}"

  info "同步数据源 ${db_id} 的 schema 索引..."
  local resp
  resp=$(api_call "$uid" POST "/openapi/getDataSourceByIdOrName" -d "{\"id\": ${db_id}}")

  echo "$resp" | python3 -c "
import sys, json
data = json.load(sys.stdin)
db_id = '${db_id}'
base = '${udir}/schema/${db_id}'

# 保存完整响应作为 index
with open(f'{base}/index.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 提取 table_schema 作为 summary
schema = data.get('table_schema', '')
with open(f'{base}/summary.json', 'w') as f:
    json.dump({'table_schema': schema, 'name': data.get('name',''), 'type': data.get('type','')}, f, ensure_ascii=False, indent=2)

# 提取术语
terms = data.get('terminologies', '')
sem_dir = '${udir}/semantic/${db_id}'
import os
os.makedirs(sem_dir, exist_ok=True)
with open(f'{sem_dir}/terminologies_raw.txt', 'w') as f:
    f.write(terms if terms else '')

print(f'schema 索引已保存: {base}/index.json')
print(f'表概要已保存: {base}/summary.json')
"
}

cmd_pull_table() {
  local uid="$1" db_id="$2" table="$3"
  local udir="${SQLBOT_HOME}/${uid}"
  mkdir -p "${udir}/schema/${db_id}/tables"

  info "同步表 ${table} 的详细信息..."
  # 这里复用 index 中的信息，因为 getDataSourceByIdOrName 已包含完整 schema
  local index_file="${udir}/schema/${db_id}/index.json"
  if [[ ! -f "$index_file" ]]; then
    info "索引不存在，先拉取..."
    cmd_pull_index "$uid" "$db_id"
  fi

  python3 -c "
import json, sys
table_name = '${table}'
with open('${index_file}') as f:
    data = json.load(f)
schema_text = data.get('table_schema', '')

# 解析 M-Schema 格式提取表信息
lines = schema_text.split('\n')
table_info = {'table_name': table_name, 'schema_raw': '', 'fields': []}
capturing = False
for line in lines:
    if table_name.lower() in line.lower():
        capturing = True
    if capturing:
        table_info['schema_raw'] += line + '\n'
        if line.strip() == '' and capturing:
            break

out_path = '${udir}/schema/${db_id}/tables/${table}.json'
with open(out_path, 'w') as f:
    json.dump(table_info, f, ensure_ascii=False, indent=2)
print(f'表详情已保存: {out_path}')
"
}

cmd_pull_tables() {
  local uid="$1" db_id="$2"
  local udir="${SQLBOT_HOME}/${uid}"
  mkdir -p "${udir}/schema/${db_id}/tables"

  local index_file="${udir}/schema/${db_id}/index.json"
  if [[ ! -f "$index_file" ]]; then
    cmd_pull_index "$uid" "$db_id"
  fi

  info "同步所有表详情..."
  python3 -c "
import json, re
with open('${index_file}') as f:
    data = json.load(f)
schema_text = data.get('table_schema', '')

# 提取所有表名 (M-Schema 格式: # table_name(...) 或 CREATE TABLE 等)
table_names = set()
for line in schema_text.split('\n'):
    line = line.strip()
    # M-Schema 格式
    m = re.match(r'^#\s+(\w+)\s*\(', line)
    if m:
        table_names.add(m.group(1))
    # CREATE TABLE 格式
    m = re.match(r'CREATE\s+TABLE\s+[\x60\"]*(\w+)', line, re.I)
    if m:
        table_names.add(m.group(1))

print(f'发现 {len(table_names)} 个表: {sorted(table_names)}')
for tbl in sorted(table_names):
    out = '${udir}/schema/${db_id}/tables/' + tbl + '.json'
    info = {'table_name': tbl, 'source': 'bulk_pull'}
    with open(out, 'w') as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
"
}

cmd_pull_semantic() {
  local uid="$1" db_id="$2"
  local udir="${SQLBOT_HOME}/${uid}"
  mkdir -p "${udir}/semantic/${db_id}"

  info "同步术语口径..."
  local resp
  resp=$(api_call "$uid" GET "/openapi/getAllTerminologiesByDataSource")

  echo "$resp" | python3 -c "
import sys, json
data = json.load(sys.stdin)
db_id = '${db_id}'
out = '${udir}/semantic/${db_id}/terminologies.json'

if isinstance(data, dict) and 'data' in data:
    terms = data['data'].get('terminologies_by_datasource', {}).get(db_id, [])
    with open(out, 'w') as f:
        json.dump(terms, f, ensure_ascii=False, indent=2)
    print(f'术语已保存 ({len(terms)} 条): {out}')
else:
    with open(out, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'术语已保存: {out}')
"
}

cmd_pull_relations() {
  local uid="$1" db_id="$2"
  local udir="${SQLBOT_HOME}/${uid}"
  mkdir -p "${udir}/relations/${db_id}"

  info "同步表关系图..."
  local resp
  resp=$(api_call "$uid" POST "/table_relation/get/${db_id}")

  local out="${udir}/relations/${db_id}/table_relations.json"
  echo "$resp" > "$out"
  info "表关系已保存: ${out}"
}

cmd_pull_permissions() {
  local uid="$1"
  local udir="${SQLBOT_HOME}/${uid}"
  mkdir -p "${udir}/permissions"

  info "同步数据源权限..."
  local resp
  resp=$(api_call "$uid" GET "/openapi/getDataSourceList")

  local out="${udir}/permissions/datasources.json"
  echo "$resp" > "$out"
  info "权限信息已保存: ${out}"
}

cmd_exec() {
  local uid="$1" db_id="$2" sql="$3" file="${4:-}"
  local udir="${SQLBOT_HOME}/${uid}"
  mkdir -p "${udir}/exports"

  if [[ -z "$file" ]]; then
    file="export_$(date +%Y%m%d_%H%M%S).csv"
  fi
  local out="${udir}/exports/${file}"

  info "执行 SQL (db_id=${db_id}): ${sql:0:100}..."

  # 使用 CSV 导出端点
  curl ${CURL_OPTS} -X POST "$(get_url "$uid")/openapi/getDataByDbIdAndSqlCsv" \
    -H "Content-Type: application/json" \
    -H "X-SQLBOT-TOKEN: $(get_token "$uid")" \
    -d "$(python3 -c "import json; print(json.dumps({'db_id':'${db_id}','sql':'''${sql}'''}))")" \
    -o "$out"

  local lines
  lines=$(wc -l < "$out" 2>/dev/null || echo 0)
  info "结果已导出: ${out} (${lines} 行)"
  echo "$out"
}

cmd_check() {
  local uid="$1" db_id="${2:-}"
  local udir="${SQLBOT_HOME}/${uid}"

  echo "=== 用户空间: ${udir} ==="
  if [[ -f "${udir}/config.json" ]]; then
    echo "  config.json: ✓"
    local url
    url=$(get_url "$uid" 2>/dev/null || echo "N/A")
    echo "  API URL: ${url}"
  else
    echo "  config.json: ✗ (未初始化)"
    return 1
  fi

  if [[ -n "$db_id" ]]; then
    echo "--- 数据源 ${db_id} ---"
    [[ -f "${udir}/schema/${db_id}/index.json" ]]    && echo "  L1 索引: ✓" || echo "  L1 索引: ✗"
    [[ -f "${udir}/schema/${db_id}/summary.json" ]]   && echo "  L2 概要: ✓" || echo "  L2 概要: ✗"
    local tc
    tc=$(ls "${udir}/schema/${db_id}/tables/" 2>/dev/null | wc -l)
    echo "  L3 表详情: ${tc} 个"
    [[ -f "${udir}/semantic/${db_id}/terminologies.json" ]] && echo "  术语: ✓" || echo "  术语: ✗"
    [[ -f "${udir}/relations/${db_id}/table_relations.json" ]] && echo "  关系: ✓" || echo "  关系: ✗"
  fi

  local ec
  ec=$(ls "${udir}/exports/" 2>/dev/null | wc -l)
  echo "  导出文件: ${ec} 个"
}

cmd_describe() {
  local uid="$1" db_id="$2"
  local udir="${SQLBOT_HOME}/${uid}"
  local summary="${udir}/schema/${db_id}/summary.json"

  if [[ ! -f "$summary" ]]; then
    info "概要不存在，先拉取..."
    cmd_pull_index "$uid" "$db_id"
  fi

  python3 -c "
import json
with open('${summary}') as f:
    data = json.load(f)
schema = data.get('table_schema', '')
if schema:
    print(schema[:5000])
else:
    print('(schema 为空)')
"
}

# ---------- main ----------
cmd="${1:--h}"
shift || true

case "$cmd" in
  -h|--help|help)      cmd_help ;;
  login)               cmd_login "$@" ;;
  init)                cmd_init "$@" ;;
  check)               cmd_check "$@" ;;
  list-ds)             cmd_list_ds "$@" ;;
  pull-index)          cmd_pull_index "$@" ;;
  pull-table)          cmd_pull_table "$@" ;;
  pull-tables)         cmd_pull_tables "$@" ;;
  pull-semantic)       cmd_pull_semantic "$@" ;;
  pull-relations)      cmd_pull_relations "$@" ;;
  pull-permissions)    cmd_pull_permissions "$@" ;;
  exec)                cmd_exec "$@" ;;
  describe)            cmd_describe "$@" ;;
  *)                   die "未知命令: $cmd (执行 run.sh -h 查看帮助)" ;;
esac
