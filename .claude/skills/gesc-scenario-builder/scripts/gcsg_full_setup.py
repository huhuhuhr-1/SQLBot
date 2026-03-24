import psycopg2
import random
import uuid
from datetime import datetime, timedelta

# 数据库配置
DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 8086,
    "user": "sqlbot",
    "password": "sqlbot"
}

DB_NAMES = ["gcsg_ops", "gcsg_governance", "gcsg_intelligence"]

# 核心表定义字典 (部分示例，实际包含更多)
TABLE_DEFS = {
    "gcsg_ops": [
        "CREATE TABLE IF NOT EXISTS abnormal_account_login (id SERIAL PRIMARY KEY, device_id VARCHAR(32), sip VARCHAR(46), dip VARCHAR(46), alert_time TIMESTAMP, login_count INT, depart_id VARCHAR(64));",
        "CREATE TABLE IF NOT EXISTS alert_attack_all (id SERIAL PRIMARY KEY, device_id VARCHAR(32), alert_id VARCHAR(64), alert_time TIMESTAMP, rule_name VARCHAR(128), risk INT, sip VARCHAR(46), dip VARCHAR(46), cve VARCHAR(64), depart_id VARCHAR(64));",
        "CREATE TABLE IF NOT EXISTS audit_behavior_web (id SERIAL PRIMARY KEY, sip VARCHAR(46), dip VARCHAR(46), start_time TIMESTAMP, domain VARCHAR(255), method VARCHAR(10), status_code INT);"
    ],
    "gcsg_governance": [
        "CREATE TABLE IF NOT EXISTS sys_department (id SERIAL PRIMARY KEY, depart_id VARCHAR(64) UNIQUE, depart_name VARCHAR(128), company_name VARCHAR(128));",
        "CREATE TABLE IF NOT EXISTS sys_device_info (id SERIAL PRIMARY KEY, device_id VARCHAR(32) UNIQUE, organs VARCHAR(128), address VARCHAR(128), state VARCHAR(2));"
    ],
    "gcsg_intelligence": [
        "CREATE TABLE IF NOT EXISTS ioc_cve_info (id SERIAL PRIMARY KEY, name VARCHAR(255) UNIQUE, name_cn VARCHAR(255), hazard_level VARCHAR(64), description TEXT);",
        "CREATE TABLE IF NOT EXISTS kb_malware_type (id SERIAL PRIMARY KEY, alert_name VARCHAR(255), threat_rule_type VARCHAR(64));"
    ]
}

def run_setup():
    # 模拟 30 张表的扩展逻辑（通过循环生成相似结构的表以达到 30+ 规模）
    for i in range(1, 25):
        TABLE_DEFS["gcsg_ops"].append(f"CREATE TABLE IF NOT EXISTS audit_extra_{i} (id SERIAL PRIMARY KEY, info TEXT, create_time TIMESTAMP);")
        TABLE_DEFS["gcsg_governance"].append(f"CREATE TABLE IF NOT EXISTS policy_extra_{i} (id SERIAL PRIMARY KEY, rule_name TEXT, enable INT);")
        TABLE_DEFS["gcsg_intelligence"].append(f"CREATE TABLE IF NOT EXISTS stats_extra_{i} (id SERIAL PRIMARY KEY, category TEXT, count INT);")

    for db_name in DB_NAMES:
        print(f"--- 正在初始化数据库: {db_name} ---")
        conn = psycopg2.connect(**DB_CONFIG, dbname=db_name)
        cur = conn.cursor()
        
        # 1. 创建表结构
        for sql in TABLE_DEFS.get(db_name, []):
            cur.execute(sql)
        
        # 2. 注入基础数据 (Governance/Intelligence)
        if db_name == "gcsg_governance":
            for i in range(100):
                cur.execute("INSERT INTO sys_department (depart_id, depart_name, company_name) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;",
                            (f"DEPT-{i:03d}", f"Department-{i}", "Global Corp"))
            for i in range(500):
                cur.execute("INSERT INTO sys_device_info (device_id, organs, address, state) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;",
                            (f"DEV-{i:04d}", "SOC Unit", f"Building {i//10}", "1"))
        
        if db_name == "gcsg_intelligence":
            for i in range(200):
                cur.execute("INSERT INTO ioc_cve_info (name, name_cn, hazard_level) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;",
                            (f"CVE-2024-{i:04d}", f"漏洞-{i}", "High"))

        # 3. 饱和式灌溉 (Ops) - 10万数据
        if db_name == "gcsg_ops":
            print("正在灌溉 100,000 条告警数据...")
            batch_size = 5000
            for b in range(0, 100000, batch_size):
                chunk = []
                for _ in range(batch_size):
                    chunk.append((
                        f"DEV-{random.randint(0, 499):04d}", f"ALRT-{uuid.uuid4().hex[:8].upper()}",
                        datetime.now() - timedelta(seconds=random.randint(0, 2592000)),
                        "Security Breach", random.randint(1, 4), "10.0.0.1", "192.168.1.1",
                        f"CVE-2024-{random.randint(0, 199):04d}", f"DEPT-{random.randint(0, 99):03d}"
                    ))
                cur.executemany("INSERT INTO alert_attack_all (device_id, alert_id, alert_time, rule_name, risk, sip, dip, cve, depart_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);", chunk)
                print(f"进度: {b + batch_size}/100000")

        conn.commit()
        cur.close()
        conn.close()
    print("--- GCSG 全局初始化完成！ ---")

if __name__ == "__main__":
    run_setup()
