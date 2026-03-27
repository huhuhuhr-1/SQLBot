import os, sys, json, requests, re, shutil
from pathlib import Path
from datetime import datetime

SQLBOT_ROOT = Path.home() / ".sqlbot"
COMMON_DIR = SQLBOT_ROOT / "_common"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[3]  # repo root: .../SQLBot


# 简化目录结构：~/.sqlbot/<uid>/ 替代 ~/.sqlbot/users/<uid>/metadata/<dbid>/
def get_user_dir(uid): return SQLBOT_ROOT / uid


def get_schema_dir(uid, dbid): return get_user_dir(uid) / "schema" / str(dbid)


def get_semantic_dir(uid, dbid): return get_user_dir(uid) / "semantic" / str(dbid)


def get_relations_dir(uid, dbid): return get_user_dir(uid) / "relations" / str(dbid)


def get_permissions_dir(uid): return get_user_dir(uid) / "permissions"


def get_cached_table_schema_path(uid, dbid): return get_schema_dir(uid, dbid) / "full_table_schema.txt"


def _load_config(uid):
    f = get_user_dir(uid) / "config.json"
    if f.exists():
        with open(f) as r: return json.load(r)
    return {}


def _save_config(uid, config):
    """Save config to file"""
    d = get_user_dir(uid)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "config.json", "w") as w: json.dump(config, w)


def login(uid, username, password):
    """
    Login with username and password to get JWT token.
    Automatically saves the token and host to config.json.
    """
    config = _load_config(uid)
    host = config.get("host")

    # 强制用户 init 时指定地址，不使用默认值
    if not host:
        print("❌ Host not configured.")
        print("   Run: bash scripts/run.sh init <user_id> <url> <token>")
        print("   Example: bash scripts/run.sh init admin http://localhost:8000 temp-token")
        sys.exit(1)

    print(f"🔄 Logging in to {host} as {username}...")

    try:
        r = requests.post(
            f"{host}/api/v1/openapi/getToken",
            headers={"Content-Type": "application/json"},
            json={"username": username, "password": password, "create_chat": False}
        )

        if r.status_code != 200:
            print(f"❌ Login failed: HTTP {r.status_code}")
            print(f"   Response: {r.text[:500]}")
            print(f"\n💡 Tips:")
            print(f"   - Check your username and password")
            print(f"   - Ensure the SQLBot server is running at {host}")
            print(f"   - If server uses xpack encryption, contact admin for API access")
            sys.exit(1)

        resp = r.json()
        if resp.get("code") != 0:
            print(f"❌ Login failed: {resp.get('msg', 'Unknown error')}")
            sys.exit(1)

        token = resp.get("data", {}).get("access_token", "")
        expire = resp.get("data", {}).get("expire", "")

        if not token:
            print("❌ Login failed: No token in response")
            sys.exit(1)

        # Save to config
        config["host"] = host
        config["token"] = token
        config["token_expire"] = expire
        config["username"] = username
        _save_config(uid, config)

        print(f"✅ Login successful!")
        print(f"   Token: {token[:30]}...")
        print(f"   Expires: {expire}")
        print(f"   Config saved to: {get_user_dir(uid) / 'config.json'}")
        return True

    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to SQLBot server at {host}")
        print(f"\n💡 Tips:")
        print(f"   - Check if the server is running")
        print(f"   - Set SQLBOT_HOST environment variable or use 'init' command to configure host")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Login error: {e}")
        sys.exit(1)


def _is_token_expired(config):
    """Check if token is expired based on expire time"""
    if not config.get("token_expire"):
        return True  # No expire info, assume expired

    try:
        # Parse expire time (format: "2026-03-27T10:30:00")
        expire_str = config["token_expire"]
        # Try different formats
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"]:
            try:
                expire_time = datetime.strptime(expire_str, fmt)
                return datetime.now() > expire_time
            except ValueError:
                continue
        # If all formats fail, assume expired
        return True
    except Exception:
        return True


def _ensure_token(uid):
    """Ensure token is valid, auto-refresh if expired"""
    config = _load_config(uid)

    if not config.get("token"):
        print("❌ No token found. Please login first:")
        print(f"   bash scripts/run.sh login {uid} <username> <password>")
        sys.exit(1)

    if _is_token_expired(config):
        print("🔄 Token expired, attempting auto-refresh...")
        username = config.get("username")
        if not username:
            print("❌ Cannot auto-refresh: username not found in config")
            print(f"   Please login again:")
            print(f"   bash scripts/run.sh login {uid} <username> <password>")
            sys.exit(1)

        # Note: We cannot auto-refresh without password
        # User needs to login again
        print("❌ Token expired and username not stored for auto-refresh")
        print(f"   Please login again:")
        print(f"   bash scripts/run.sh login {uid} <username> <password>")
        sys.exit(1)

    return config["token"]


def init_config(uid, url, token):
    d = get_user_dir(uid)
    d.mkdir(parents=True, exist_ok=True)
    d.joinpath("exports").mkdir(parents=True, exist_ok=True)
    with open(d / "config.json", "w") as w:
        json.dump({"host": url.rstrip("/"), "token": token}, w)
    print(f"✅ Initialized at {d}")
    # Ensure common SQL-generation knowledge exists for skills
    try:
        pull_knowledge_common(uid)
    except Exception as e:
        print(f"⚠️ Knowledge sync skipped: {e}")


def get_info(uid):
    c = _load_config(uid)
    if not c.get("host"):
        print("❌ No host configured. Please run 'init' or 'login' first.")
        sys.exit(1)

    # Check token validity
    token = _ensure_token(uid)
    return c["host"], token


def pull_index(uid, dbid):
    h, t = get_info(uid)
    r = requests.post(f"{h}/api/v1/openapi/getDataSourceByIdOrName", headers={"X-SQLBOT-TOKEN": t},
                      json={"id": str(dbid)})
    data = r.json().get("data", {})
    schema_dir = get_schema_dir(uid, dbid)
    schema_dir.mkdir(parents=True, exist_ok=True)
    with open(schema_dir / "index.json", "w") as f:
        json.dump({"id": data.get("id"), "name": data.get("name")}, f)
    full = data.get("table_schema", "")
    # 缓存全量 table_schema，避免后续逐表拉取时反复网络请求
    with open(get_cached_table_schema_path(uid, dbid), "w", encoding="utf-8") as f:
        f.write(full or "")
    summary = []
    parts = re.split(r"(# Table:)", full)
    for i in range(1, len(parts), 2):
        c = parts[i + 1]
        if c:
            h_l = c.split("\n")[0]
            m = re.match(r"\s*([^,\n]+)(?:,\s*(.*))?", h_l)
            if m:
                # comment 可能不存在（regex 的第二组是可选的），避免 None.strip() 直接崩溃
                summary.append({
                    "table": (m.group(1) or "").strip(),
                    "comment": (m.group(2) or "").strip()
                })
    with open(schema_dir / "summary.json", "w") as f:
        json.dump(summary, f)
    print(f"✅ Synced Index for DB {dbid}")


def check_metadata(uid, dbid):
    """
    本地检查某库元数据是否已同步到足够粒度：
    - index.json
    - schema/summary.json
    - schema/tables/*.json（L3，可选）
    """
    schema_dir = get_schema_dir(uid, dbid)
    index_p = schema_dir / "index.json"
    summary_p = schema_dir / "summary.json"
    tables_dir = schema_dir / "tables"

    ok = True
    msgs = []
    if not index_p.exists():
        ok = False
        msgs.append("missing index.json")
    if not summary_p.exists():
        ok = False
        msgs.append("missing schema/summary.json")

    l3_count = 0
    if tables_dir.exists() and tables_dir.is_dir():
        try:
            l3_count = len([p for p in tables_dir.glob("*.json")])
        except Exception:
            l3_count = 0

    if ok:
        print(f"✅ Metadata OK for DB {dbid}. L3 tables json count: {l3_count}")
    else:
        print(f"❌ Metadata incomplete for DB {dbid}: {', '.join(msgs)}")
        print(f"ℹ️ Current L3 tables json count: {l3_count}")
        sys.exit(1)


def pull_permissions(uid):
    """
    拉取当前用户在 SQLBot 中可见的数据源清单（权限上下文）。
    落盘：~/.sqlbot/users/<uid>/permissions/datasources.json
    """
    h, t = get_info(uid)
    r = requests.get(f"{h}/api/v1/openapi/getDataSourceList", headers={"X-SQLBOT-TOKEN": t})
    if r.status_code != 200:
        print(f"❌ Error: {r.text}")
        sys.exit(1)
    data = r.json().get("data", []) or []
    d = get_permissions_dir(uid)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "datasources.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Synced permissions for user {uid}: {len(data)} datasources")


def pull_semantic(uid, dbid):
    """
    拉取该库的术语/口径（terminologies）。
    落盘：~/.sqlbot/users/<uid>/metadata/<dbid>/semantic/terminologies.(json|txt)
    """
    h, t = get_info(uid)
    r = requests.post(
        f"{h}/api/v1/openapi/getDataSourceByIdOrName",
        headers={"X-SQLBOT-TOKEN": t},
        json={"id": str(dbid)},
    )
    if r.status_code != 200:
        print(f"❌ Error: {r.text}")
        sys.exit(1)
    data = r.json().get("data", {}) or {}
    terminologies = data.get("terminologies") or ""

    d = get_semantic_dir(uid, dbid)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "terminologies.json", "w", encoding="utf-8") as f:
        json.dump({"terminologies": terminologies}, f, ensure_ascii=False, indent=2)
    with open(d / "terminologies.txt", "w", encoding="utf-8") as f:
        f.write(terminologies)
    print(f"✅ Synced semantic(terminologies) for DB {dbid}")


def pull_terminologies_all(uid):
    """
    拉取“全部可见数据源 + 每个数据源的全量术语”，并按 db_id 写入：
    ~/.sqlbot/users/<uid>/metadata/<db_id>/semantic/terminologies.json|terminologies.txt
    """
    h, t = get_info(uid)
    r = requests.get(
        f"{h}/api/v1/openapi/getAllTerminologiesByDataSource",
        headers={"X-SQLBOT-TOKEN": t},
    )
    if r.status_code != 200:
        print(f"❌ Error: {r.text}")
        sys.exit(1)
    data = r.json().get("data") or {}
    terminologies_by_ds = data.get("terminologies_by_datasource") or {}

    for dbid_str, terms in terminologies_by_ds.items():
        try:
            dbid = int(dbid_str)
        except Exception:
            continue
        d = get_semantic_dir(uid, dbid)
        d.mkdir(parents=True, exist_ok=True)

        # terms: list[TerminologyInfo] -> store as raw list
        with open(d / "terminologies.json", "w", encoding="utf-8") as f:
            json.dump({"terminologies": terms}, f, ensure_ascii=False, indent=2)

        # Provide a plain-text prompt-friendly format
        # (skills/LLM 可直接读；你如果希望 XML 格式我也可以再调整)
        blocks = []
        if isinstance(terms, list):
            for term in terms:
                w = term.get("word") or ""
                desc = term.get("description") or ""
                other = term.get("other_words") or []
                other_s = ", ".join(other) if isinstance(other, list) else str(other)
                blocks.append(f"- {w} ({other_s})\n  {desc}".strip())
        txt = "\n\n".join(blocks)
        with open(d / "terminologies.txt", "w", encoding="utf-8") as f:
            f.write(txt)

        print(f"✅ Synced all terminologies for DB {dbid}: {len(terms) if isinstance(terms, list) else 0} terms")


def pull_relations(uid, dbid):
    """
    拉取表关系（table_relation graph）。
    落盘：~/.sqlbot/users/<uid>/metadata/<dbid>/relations/table_relations.json
    """
    h, t = get_info(uid)
    r = requests.post(
        f"{h}/api/v1/table_relation/get/{dbid}",
        headers={"X-SQLBOT-TOKEN": t},
        json={},
    )
    if r.status_code != 200:
        print(f"❌ Error: {r.text}")
        sys.exit(1)
    resp = r.json().get("data", []) or []

    d = get_relations_dir(uid, dbid)
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "table_relations.json", "w", encoding="utf-8") as f:
        json.dump({"db_id": dbid, "relations": resp}, f, ensure_ascii=False, indent=2)
    print(f"✅ Synced relations for DB {dbid}: {len(resp)} relations/edges")


def pull_knowledge_common(uid):
    """
    同步技能所需的“通用上下文”到 ~/.sqlbot/_common/：
    - engines/*.yaml
    - sql_examples/*.yaml
    - rules/template.yaml（用于调试/复用）
    """
    engines_src = SCRIPT_DIR.parent / "references" / "engines"
    if engines_src.exists():
        engines_dst = COMMON_DIR / "engines"
        engines_dst.mkdir(parents=True, exist_ok=True)
        for p in engines_src.glob("*.yaml"):
            dst = engines_dst / p.name
            if not dst.exists():
                shutil.copy2(p, dst)

    examples_src = REPO_ROOT / "backend/templates/sql_examples"
    if examples_src.exists():
        examples_dst = COMMON_DIR / "sql_examples"
        examples_dst.mkdir(parents=True, exist_ok=True)
        for p in examples_src.glob("*.yaml"):
            dst = examples_dst / p.name
            if not dst.exists():
                shutil.copy2(p, dst)

    template_src = REPO_ROOT / "backend/templates/template.yaml"
    template_dst_dir = COMMON_DIR / "rules"
    template_dst_dir.mkdir(parents=True, exist_ok=True)
    template_dst = template_dst_dir / "template.yaml"
    if template_src.exists() and not template_dst.exists():
        shutil.copy2(template_src, template_dst)

    print(f"✅ Synced common knowledge into {COMMON_DIR}")


def _load_full_table_schema(uid, dbid):
    cached = get_cached_table_schema_path(uid, dbid)
    if cached.exists():
        return cached.read_text(encoding="utf-8")
    # fallback: fetch from server (only if cache missing)
    h, t = get_info(uid)
    r = requests.post(f"{h}/api/v1/openapi/getDataSourceByIdOrName", headers={"X-SQLBOT-TOKEN": t},
                      json={"id": str(dbid)})
    return r.json().get("data", {}).get("table_schema", "") or ""


def pull_table(uid, dbid, tname):
    full = _load_full_table_schema(uid, dbid)
    p = rf"# Table:\s*{re.escape(tname)}.*?(?=# Table:|$)"
    m = re.search(p, full, re.DOTALL)
    if m:
        d = get_schema_dir(uid, dbid) / "tables"
        d.mkdir(parents=True, exist_ok=True)
        with open(d / f"{tname}.json", "w") as f:
            json.dump({"table": tname, "ddl": m.group(0)}, f)
        print(f"✅ Synced {tname}")
    else:
        print(f"⚠️ Table not found in cached schema: {tname}")


def pull_tables(uid, dbid):
    """
    拉取某个库的所有表 L3 元数据（每张表写 schema/tables/<table>.json）。
    通过本地缓存的 full table_schema 做一次性解析，避免逐表重复网络请求。
    """
    full = _load_full_table_schema(uid, dbid)
    d = get_schema_dir(uid, dbid) / "tables"
    d.mkdir(parents=True, exist_ok=True)

    parts = re.split(r"(# Table:)", full)
    written = 0
    for i in range(1, len(parts), 2):
        c = parts[i + 1]
        if not c:
            continue
        first_line = c.split("\n")[0]
        m = re.match(r"\s*([^,\n]+)(?:,\s*(.*))?", first_line)
        if not m:
            continue
        tname = (m.group(1) or "").strip()
        if not tname:
            continue
        ddl = "# Table:" + c
        with open(d / f"{tname}.json", "w") as f:
            json.dump({"table": tname, "ddl": ddl}, f)
        written += 1

    print(f"✅ Synced all tables for DB {dbid}: {written} tables")


def exec_sql(uid, dbid, sql, fname):
    h, t = get_info(uid)
    r = requests.post(f"{h}/api/v1/openapi/getDataByDbIdAndSqlCsv", headers={"X-SQLBOT-TOKEN": t},
                      json={"db_id": str(dbid), "sql": sql}, stream=True)
    if r.status_code != 200:
        print(f"❌ Error: {r.text}")
        sys.exit(1)
    p = get_user_dir(uid) / "exports" / fname
    with open(p, "wb") as f:
        for chunk in r.iter_content(8192): f.write(chunk)
    print(f"✅ Saved to {p}")


if __name__ == "__main__":
    cmd, uid = sys.argv[1], sys.argv[2]
    if cmd == "login":
        login(uid, sys.argv[3], sys.argv[4])
    elif cmd == "init":
        init_config(uid, sys.argv[3], sys.argv[4])
    elif cmd == "check":
        check_metadata(uid, sys.argv[3])
    elif cmd == "pull-permissions":
        pull_permissions(uid)
    elif cmd == "pull-terminologies-all":
        pull_terminologies_all(uid)
    elif cmd == "pull-semantic":
        pull_semantic(uid, sys.argv[3])
    elif cmd == "pull-relations":
        pull_relations(uid, sys.argv[3])
    elif cmd == "pull-knowledge-common":
        pull_knowledge_common(uid)
    elif cmd == "pull-index":
        pull_index(uid, sys.argv[3])
    elif cmd == "pull-table":
        pull_table(uid, sys.argv[3], sys.argv[4])
    elif cmd == "pull-tables":
        pull_tables(uid, sys.argv[3])
    elif cmd == "exec":
        exec_sql(uid, sys.argv[3], sys.argv[4], sys.argv[5])
