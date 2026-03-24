import os
import sys
import json
import requests
import re
from pathlib import Path

METADATA_DIR = Path(".sqlbot/metadata")
CONFIG_FILE = Path(".sqlbot/config.json")

def _save_config(config):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Load existing config to merge
    current = _load_config()
    current.update(config)
    with open(CONFIG_FILE, "w") as f:
        json.dump(current, f, indent=2)

def _load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def init_config(ip, port, user, password):
    # Ensure protocol is included
    host = ip if ip.startswith("http") else f"http://{ip}"
    host = f"{host}:{port}"
    
    # Test connection and get initial token
    url = f"{host}/api/v1/openapi/getToken"
    payload = {"username": user, "password": password, "create_chat": False}
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        resp_json = response.json()
        data = resp_json.get("data") or {}
        token = data.get("access_token") or resp_json.get("access_token")
        
        if token:
            _save_config({
                "host": host,
                "user": user,
                "pass": password,
                "token": token
            })
            print(f"✅ Initialization successful! Connected to {host}")
            print(f"Configuration saved to {CONFIG_FILE}")
        else:
            print(f"❌ Error: Could not find token in response from {url}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Initialization failed: {e}")
        sys.exit(1)

def get_connection_info():
    config = _load_config()
    host = os.environ.get("SQLBOT_HOST") or config.get("host")
    user = os.environ.get("SQLBOT_USER") or config.get("user")
    password = os.environ.get("SQLBOT_PASS") or config.get("pass")
    token = config.get("token")
    
    if not all([host, user, password]):
        print("Error: SQLBot credentials not found. Please run: bash scripts/run.sh init <ip> <port> <user> <pass>")
        sys.exit(1)
        
    return host.rstrip('/'), user, password, token

def get_token():
    host, user, password, cached_token = get_connection_info()
    
    # In a real scenario, we might want to check token expiry
    # For now, let's use the cached one if available
    if cached_token:
        return cached_token

    url = f"{host}/api/v1/openapi/getToken"
    payload = {"username": user, "password": password, "create_chat": False}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        resp_json = response.json()
        data = resp_json.get("data") or {}
        token = data.get("access_token") or resp_json.get("access_token")
        
        if not token:
            print(f"Error: Could not find token in response from {url}")
            sys.exit(1)
            
        _save_config({"token": token})
        return token
    except Exception as e:
        print(f"Error fetching token from {url}: {e}")
        sys.exit(1)

def list_datasources():
    host, _, _, _ = get_connection_info()
    token = get_token()
    url = f"{host}/api/v1/openapi/getDataSourceList"
    headers = {"X-SQLBOT-TOKEN": token}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        resp_json = response.json()
        if isinstance(resp_json, dict) and "data" in resp_json:
            return resp_json["data"]
        return resp_json
    except Exception as e:
        print(f"Error listing datasources from {url}: {e}")
        sys.exit(1)

def sync_metadata(db_id):
    host, user, _, _ = get_connection_info()
    token = get_token()
    headers = {"X-SQLBOT-TOKEN": token}
    
    db_dir = METADATA_DIR / str(db_id)
    details_dir = db_dir / "details"
    db_dir.mkdir(parents=True, exist_ok=True)
    details_dir.mkdir(parents=True, exist_ok=True)
    
    url = f"{host}/api/v1/openapi/getDataSourceByIdOrName"
    payload = {"id": str(db_id)}
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        resp_json = response.json()
        
        ds_info = resp_json.get("data") if isinstance(resp_json, dict) and "data" in resp_json and isinstance(resp_json["data"], dict) else resp_json
            
        full_schema = ds_info.get("table_schema", "")
        
        tables_summary = []
        parts = re.split(r"(# Table:)", full_schema)
        
        for i in range(1, len(parts), 2):
            marker = parts[i]
            content = parts[i+1] if i+1 < len(parts) else ""
            block = marker + content
            
            header_line = content.split("\n")[0]
            header_match = re.match(r"\s*([^,\n]+)(?:,\s*(.*))?", header_line)
            if header_match:
                table_name = header_match.group(1).strip()
                table_comment = header_match.group(2).strip() if header_match.group(2) else ""
                
                tables_summary.append({
                    "table": table_name,
                    "comment": table_comment
                })
                
                with open(details_dir / f"{table_name}.json", "w") as f:
                    json.dump({"table": table_name, "comment": table_comment, "raw_schema": block}, f, indent=2, ensure_ascii=False)
        
        with open(db_dir / "tables_summary.json", "w") as f:
            json.dump(tables_summary, f, indent=2, ensure_ascii=False)
            
        if "terminologies" in ds_info:
             with open(db_dir / "terminologies.json", "w") as f:
                json.dump(ds_info["terminologies"], f, indent=2, ensure_ascii=False)
        
        print(f"Metadata synced for DB {db_id} to {db_dir}")
        print(f"Found {len(tables_summary)} tables.")
        return ds_info
    except Exception as e:
        print(f"Error syncing metadata for DB {db_id} from {url}: {e}")
        sys.exit(1)

def execute_sql(db_id, sql, output_file):
    host, _, _, _ = get_connection_info()
    token = get_token()
    url = f"{host}/api/v1/openapi/getDataByDbIdAndSqlCsv"
    headers = {
        "X-SQLBOT-TOKEN": token,
        "Content-Type": "application/json"
    }
    payload = {"db_id": str(db_id), "sql": sql}
    
    try:
        response = requests.post(url, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        with open(output_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Data saved to {output_file}")
    except Exception as e:
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                print(f"SQL execution error: {json.dumps(error_data, ensure_ascii=False)}")
            except:
                print(f"SQL execution error: {e}")
        else:
            print(f"Error executing SQL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 sqlbot_utils.py [init|list|sync|exec] ...")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "init":
        if len(sys.argv) < 6:
            print("Usage: init <ip> <port> <user> <pass>")
            sys.exit(1)
        init_config(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "list":
        res = list_datasources()
        print(json.dumps(res, indent=2, ensure_ascii=False))
    elif cmd == "sync":
        if len(sys.argv) < 3:
            print("Usage: sync <db_id>")
            sys.exit(1)
        sync_metadata(sys.argv[2])
    elif cmd == "exec":
        if len(sys.argv) < 5:
            print("Usage: exec <db_id> <sql> <output_file>")
            sys.exit(1)
        execute_sql(sys.argv[2], sys.argv[3], sys.argv[4])
