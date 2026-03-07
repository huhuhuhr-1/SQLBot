#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为执行记录分析生成 ECharts 图表配置
"""

import sys
sys.path.insert(0, '/home/huhuhuhr/code/SQLBot/.claude/skills/echarts-renderer/scripts')

import json
import os

# 读取所有分析结果
results_dir = "/home/huhuhuhr/code/SQLBot/tmp/analysis_results"

# 分析配置：包含 SQL、数据、图表类型和问题
ANALYSIS_CONFIG = [
    {
        "name": "query1_status_distribution",
        "title": "执行状态分布",
        "chart_type": "pie",
        "description": "统计各个执行状态的任务数量和占比",
        "sql": 'SELECT "status" AS "执行状态", COUNT("id") AS "任务数量" FROM "public"."execution_records" GROUP BY "status"'
    },
    {
        "name": "query2_top_tasks",
        "title": "任务执行频率 TOP 10",
        "chart_type": "column",
        "description": "按 task_id 统计执行次数最多的前10个任务",
        "sql": 'SELECT "task_id", "task_name", COUNT("id") AS "执行次数" FROM "public"."execution_records" GROUP BY "task_id", "task_name" ORDER BY "执行次数" DESC LIMIT 10'
    },
    {
        "name": "query3_elapsed_time_stats",
        "title": "执行耗时统计",
        "chart_type": "table",
        "description": "计算所有任务的平均耗时、最大耗时、最小耗时、中位数耗时",
        "sql": 'SELECT ROUND(AVG("elapsed_time"::numeric) / 1000.0, 2) AS "平均耗时_秒", ROUND(MAX("elapsed_time"::numeric) / 1000.0, 2) AS "最大耗时_秒" FROM "public"."execution_records"'
    },
    {
        "name": "query4_daily_trend",
        "title": "每日执行趋势",
        "chart_type": "line",
        "description": "按日期统计任务执行数量和平均耗时",
        "sql": 'SELECT TO_CHAR(TO_TIMESTAMP("start_time" / 1000), \'YYYY-MM-DD\') AS "日期", COUNT("id") AS "执行次数" FROM "public"."execution_records" GROUP BY "日期" ORDER BY "日期"'
    },
    {
        "name": "query5_trigger_type",
        "title": "触发类型分布",
        "chart_type": "pie",
        "description": "统计不同触发类型的任务数量和占比",
        "sql": 'SELECT COALESCE("trigger_type", \'未知\') AS "触发类型", COUNT("id") AS "任务数量" FROM "public"."execution_records" GROUP BY "trigger_type"'
    },
    {
        "name": "query6_queue_distribution",
        "title": "执行队列分布",
        "chart_type": "column",
        "description": "统计各执行队列的任务数量和平均耗时",
        "sql": 'SELECT COALESCE("execute_queue_name", \'默认队列\') AS "队列名称", COUNT("id") AS "任务数量" FROM "public"."execution_records" GROUP BY "execute_queue_name"'
    },
    {
        "name": "query7_status_elapsed",
        "title": "状态与耗时关系",
        "chart_type": "column",
        "description": "分析不同状态下的平均耗时",
        "sql": 'SELECT "status", COUNT("id") AS "任务数量", ROUND(AVG("elapsed_time"::numeric) / 1000.0, 2) AS "平均耗时_秒" FROM "public"."execution_records" WHERE "elapsed_time" IS NOT NULL GROUP BY "status"'
    }
]

def generate_chart_config(name, sql, data, chart_type, title):
    """生成单个图表配置"""

    # 分析字段类型
    fields = []
    if data and len(data) > 0:
        first_row = data[0]
        for key, value in first_row.items():
            field_type = "string" if isinstance(value, str) else "number"
            fields.append({"name": key, "value": key, "type": field_type})

    # 识别维度和指标
    dimension_field = None
    metric_field = None

    for field in fields:
        if field["type"] == "string":
            dimension_field = field["value"]
            break

    for field in fields:
        if field["type"] == "number" and "数量" in field["name"]:
            metric_field = field["value"]
            break
        elif field["type"] == "number" and not metric_field:
            metric_field = field["value"]

    # 根据图表类型生成配置
    config = {
        "title": title,
        "type": chart_type,
        "data": data
    }

    if chart_type == "pie":
        config["axis"] = {
            "series": {"name": dimension_field or "分类", "value": dimension_field or fields[0]["value"] if fields else "category"},
            "y": {"name": metric_field or "数值", "value": metric_field or fields[1]["value"] if len(fields) > 1 else "value"}
        }
    elif chart_type in ["column", "bar", "line"]:
        config["axis"] = {
            "x": {"name": dimension_field or "X轴", "value": dimension_field or fields[0]["value"] if fields else "x"},
            "y": {"name": metric_field or "Y轴", "value": metric_field or fields[1]["value"] if len(fields) > 1 else "y"}
        }
    elif chart_type == "table":
        config["columns"] = [{"name": f["name"], "value": f["value"]} for f in fields]

    return config

def main():
    """生成所有图表配置"""

    output_dir = "/home/huhuhuhr/code/SQLBot/tmp/charts"
    os.makedirs(output_dir, exist_ok=True)

    all_charts = []

    for analysis in ANALYSIS_CONFIG:
        name = analysis["name"]
        title = analysis["title"]
        chart_type = analysis["chart_type"]
        sql = analysis["sql"]

        # 读取数据
        data_file = os.path.join(results_dir, f"{name}.json")
        if not os.path.exists(data_file):
            print(f"⚠️  跳过 {name}: 数据文件不存在")
            continue

        with open(data_file, 'r', encoding='utf-8') as f:
            result = json.load(f)

        if not result.get("success"):
            print(f"⚠️  跳过 {name}: 查询失败")
            continue

        data = result.get("data", [])

        # 生成图表配置
        chart_config = generate_chart_config(name, sql, data, chart_type, title)
        chart_config["sql"] = sql
        chart_config["description"] = analysis["description"]

        # 保存图表配置
        chart_file = os.path.join(output_dir, f"{name}_chart.json")
        with open(chart_file, 'w', encoding='utf-8') as f:
            json.dump(chart_config, f, ensure_ascii=False, indent=2)

        print(f"✅ 生成图表配置: {name} ({chart_type})")
        all_charts.append(chart_config)

    # 保存所有图表配置汇总
    summary_file = os.path.join(output_dir, "all_charts.json")
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(all_charts, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ 共生成 {len(all_charts)} 个图表配置")
    print(f"💾 配置文件已保存到: {output_dir}")
    print(f"{'='*60}")

    return all_charts

if __name__ == "__main__":
    main()