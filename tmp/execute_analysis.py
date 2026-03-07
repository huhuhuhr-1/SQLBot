#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行 execution_records 表多维度分析
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

# SQL 查询列表
QUERIES = {
    "query1_status_distribution": """
    SELECT
      "status" AS "执行状态",
      COUNT("id") AS "任务数量",
      ROUND(COUNT("id") * 100.0 / SUM(COUNT("id")) OVER(), 2) AS "占比"
      FROM "public"."execution_records"
    GROUP BY "status"
    ORDER BY "任务数量" DESC
    """,

    "query2_top_tasks": """
    SELECT
      "task_id" AS "任务ID",
      "task_name" AS "任务名称",
      COUNT("id") AS "执行次数",
      ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒"
      FROM "public"."execution_records"
    GROUP BY "task_id", "task_name"
    ORDER BY "执行次数" DESC
    LIMIT 10
    """,

    "query3_elapsed_time_stats": """
    SELECT
      ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒",
      ROUND(MAX("elapsed_time") / 1000.0, 2) AS "最大耗时_秒",
      ROUND(MIN("elapsed_time") / 1000.0, 2) AS "最小耗时_秒",
      ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY "elapsed_time") / 1000.0, 2) AS "中位数耗时_秒",
      ROUND(STDDEV("elapsed_time") / 1000.0, 2) AS "标准差_秒"
      FROM "public"."execution_records"
    WHERE "elapsed_time" IS NOT NULL
    """,

    "query4_daily_trend": """
    SELECT
      TO_CHAR(TO_TIMESTAMP("start_time" / 1000), 'YYYY-MM-DD') AS "日期",
      COUNT("id") AS "执行次数",
      ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒",
      COUNT(CASE WHEN "status" = 'SUCCESS' THEN 1 END) AS "成功数",
      COUNT(CASE WHEN "status" != 'SUCCESS' THEN 1 END) AS "失败数"
      FROM "public"."execution_records"
    WHERE "start_time" IS NOT NULL
    GROUP BY TO_CHAR(TO_TIMESTAMP("start_time" / 1000), 'YYYY-MM-DD')
    ORDER BY "日期" ASC
    """,

    "query5_trigger_type": """
    SELECT
      COALESCE("trigger_type", '未知') AS "触发类型",
      COUNT("id") AS "任务数量",
      ROUND(COUNT("id") * 100.0 / SUM(COUNT("id")) OVER(), 2) AS "占比",
      ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒"
      FROM "public"."execution_records"
    GROUP BY "trigger_type"
    ORDER BY "任务数量" DESC
    """,

    "query6_queue_distribution": """
    SELECT
      COALESCE("execute_queue_name", '默认队列') AS "队列名称",
      COUNT("id") AS "任务数量",
      ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒",
      ROUND(MAX("elapsed_time") / 1000.0, 2) AS "最大耗时_秒"
      FROM "public"."execution_records"
    GROUP BY "execute_queue_name"
    ORDER BY "任务数量" DESC
    """,

    "query7_status_elapsed": """
    SELECT
      "status" AS "执行状态",
      COUNT("id") AS "任务数量",
      ROUND(AVG("elapsed_time") / 1000.0, 2) AS "平均耗时_秒",
      ROUND(MIN("elapsed_time") / 1000.0, 2) AS "最小耗时_秒",
      ROUND(MAX("elapsed_time") / 1000.0, 2) AS "最大耗时_秒"
      FROM "public"."execution_records"
    WHERE "elapsed_time" IS NOT NULL
    GROUP BY "status"
    ORDER BY "平均耗时_秒" DESC
    """
}

def execute_all_queries():
    """执行所有分析查询"""

    # 创建输出目录
    output_dir = "/home/huhuhuhr/code/SQLBot/tmp/analysis_results"
    os.makedirs(output_dir, exist_ok=True)

    results = {}

    for query_name, sql in QUERIES.items():
        print(f"\n{'='*60}")
        print(f"执行查询: {query_name}")
        print(f"{'='*60}")

        try:
            result = execute_sql(
                db_type=DB_CONFIG["db_type"],
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
                username=DB_CONFIG["username"],
                password=DB_CONFIG["password"],
                database=DB_CONFIG["database"],
                sql=sql.strip(),
                timeout=30,
                read_only=True
            )

            if result["success"]:
                print(f"✅ 成功! 获取 {result['row_count']} 行数据")
                results[query_name] = result

                # 保存结果到 JSON 文件
                output_file = os.path.join(output_dir, f"{query_name}.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"💾 结果已保存到: {output_file}")

                # 打印前几行数据预览
                if result['data']:
                    print("\n数据预览:")
                    print(json.dumps(result['data'][:3], ensure_ascii=False, indent=2))
            else:
                print(f"❌ 执行失败: {result.get('error', '未知错误')}")
                results[query_name] = {"success": False, "error": result.get('error')}

        except Exception as e:
            print(f"❌ 异常: {str(e)}")
            results[query_name] = {"success": False, "error": str(e)}

    # 保存汇总结果
    summary_file = os.path.join(output_dir, "all_analysis_results.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ 所有查询执行完成!")
    print(f"💾 汇总结果已保存到: {summary_file}")
    print(f"{'='*60}")

    return results

if __name__ == "__main__":
    execute_all_queries()