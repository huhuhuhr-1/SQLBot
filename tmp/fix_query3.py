#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复并重新执行查询3: 执行耗时统计分析
"""

import sys
sys.path.insert(0, '/home/huhuhuhr/code/SQLBot/.claude/skills/sql-executor/scripts')

from execute_sql import execute_sql
import json
import os

# 数据库连接配置
DB_CONFIG = {
    "db_type": "pg",
    "host": "localhost",
    "port": 17082,
    "username": "sqlbot",
    "password": "sqlbot",
    "database": "dix_scheduler"
}

# 修复后的 SQL（去掉 ROUND，先转换类型）
QUERY3_FIXED = """
SELECT
  ROUND(AVG("elapsed_time"::numeric) / 1000.0, 2) AS "平均耗时_秒",
  ROUND(MAX("elapsed_time"::numeric) / 1000.0, 2) AS "最大耗时_秒",
  ROUND(MIN("elapsed_time"::numeric) / 1000.0, 2) AS "最小耗时_秒",
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "elapsed_time")::numeric / 1000.0, 2) AS "中位数耗时_秒",
  ROUND(STDDEV("elapsed_time")::numeric / 1000.0, 2) AS "标准差_秒"
  FROM "public"."execution_records"
WHERE "elapsed_time" IS NOT NULL
"""

print("执行修复后的查询3...")

try:
    result = execute_sql(
        db_type=DB_CONFIG["db_type"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        username=DB_CONFIG["username"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        sql=QUERY3_FIXED.strip(),
        timeout=30,
        read_only=True
    )

    if result["success"]:
        print(f"✅ 成功! 获取 {result['row_count']} 行数据")

        # 保存结果
        output_dir = "/home/huhuhuhr/code/SQLBot/tmp/analysis_results"
        output_file = os.path.join(output_dir, "query3_elapsed_time_stats.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"💾 结果已保存到: {output_file}")

        # 打印数据
        print("\n数据:")
        print(json.dumps(result['data'], ensure_ascii=False, indent=2))
    else:
        print(f"❌ 执行失败: {result.get('error', '未知错误')}")

except Exception as e:
    print(f"❌ 异常: {str(e)}")