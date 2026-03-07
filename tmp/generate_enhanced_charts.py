#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成多类型 ECharts 可视化图表
"""

import json
import os

def create_chart_config(chart_id, title, chart_type, data, x_field=None, y_field=None, series_field=None):
    """创建 ECharts 图表配置"""

    config = {
        "id": chart_id,
        "title": {
            "text": title,
            "left": "center",
            "textStyle": {
                "fontSize": 18,
                "fontWeight": "bold"
            }
        },
        "tooltip": {
            "trigger": "item" if chart_type == "pie" else "axis"
        },
        "legend": {
            "orient": "vertical",
            "left": "left" if chart_type == "pie" else "top"
        }
    }

    if chart_type == "pie":
        # 饼图配置
        categories = [item[x_field] for item in data]
        values = [item[y_field] for item in data]

        config["series"] = [{
            "name": title,
            "type": "pie",
            "radius": "50%",
            "data": [{"name": cat, "value": val} for cat, val in zip(categories, values)],
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowOffsetX": 0,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            }
        }]

    elif chart_type in ["bar", "column"]:
        # 柱状图/条形图配置
        categories = [item[x_field] for item in data]
        values = [item[y_field] for item in data]

        is_horizontal = chart_type == "bar"

        config["xAxis"] = {
            "type": "category" if not is_horizontal else "value",
            "data": categories if not is_horizontal else None
        } if not is_horizontal else {
            "type": "value"
        }

        config["yAxis"] = {
            "type": "value" if not is_horizontal else "category",
            "data": categories if is_horizontal else None
        } if not is_horizontal else {
            "type": "category",
            "data": categories
        }

        config["series"] = [{
            "name": y_field,
            "type": "bar",
            "data": values,
            "itemStyle": {
                "color": "#5470c6"
            }
        }]

    elif chart_type == "line":
        # 折线图配置
        categories = [item[x_field] for item in data]
        values = [item[y_field] for item in data]

        config["xAxis"] = {
            "type": "category",
            "data": categories
        }

        config["yAxis"] = {
            "type": "value"
        }

        config["series"] = [{
            "name": y_field,
            "type": "line",
            "data": values,
            "smooth": True,
            "itemStyle": {
                "color": "#5470c6"
            },
            "areaStyle": {
                "opacity": 0.3
            }
        }]

    elif chart_type == "gauge":
        # 仪表盘配置
        if data and len(data) > 0:
            value = data[0][y_field] if isinstance(data[0], dict) else data[0]
            config["series"] = [{
                "type": "gauge",
                "startAngle": 180,
                "endAngle": 0,
                "min": 0,
                "max": 100,
                "splitNumber": 10,
                "axisLine": {
                    "lineStyle": {
                        "width": 20,
                        "color": [[0.3, "#67e0e3"], [0.7, "#37a2da"], [1, "#fd666d"]]
                    }
                },
                "pointer": {
                    "icon": "path://M12.8,0.7l12,40.1H0.7L12.8,0.7z",
                    "length": "12%",
                    "width": 20,
                    "offsetCenter": [0, "-60%"],
                    "itemStyle": {
                        "color": "auto"
                    }
                },
                "axisTick": {
                    "length": 12,
                    "lineStyle": {
                        "color": "auto",
                        "width": 2
                    }
                },
                "splitLine": {
                    "length": 20,
                    "lineStyle": {
                        "color": "auto",
                        "width": 5
                    }
                },
                "axisLabel": {
                    "color": "#464646",
                    "fontSize": 20,
                    "distance": -60
                },
                "title": {
                    "offsetCenter": [0, "-20%"],
                    "fontSize": 20
                },
                "detail": {
                    "fontSize": 40,
                    "offsetCenter": [0, "0%"],
                    "valueAnimation": True,
                    "formatter": "{value}%",
                    "color": "auto"
                },
                "data": [{"value": value, "name": "成功率"}]
            }]

    elif chart_type == "scatter":
        # 散点图配置
        x_values = [item[x_field] for item in data]
        y_values = [item[y_field] for item in data]

        config["xAxis"] = {
            "type": "value",
            "scale": True
        }

        config["yAxis"] = {
            "type": "value",
            "scale": True
        }

        config["series"] = [{
            "type": "scatter",
            "data": [[x, y] for x, y in zip(x_values, y_values)],
            "symbolSize": 10,
            "itemStyle": {
                "color": "#5470c6"
            }
        }]

    elif chart_type == "radar":
        # 雷达图配置
        indicators = []
        series_data = []

        if data and len(data) > 0:
            # 假设第一列是指标名，其余是数值
            for key in data[0].keys():
                if key != x_field:
                    indicators.append({"name": key, "max": 100})

            for item in data:
                series_data.append({
                    "value": [item[k] for k in data[0].keys() if k != x_field],
                    "name": item[x_field]
                })

        config["radar"] = {
            "indicator": indicators
        }

        config["series"] = [{
            "type": "radar",
            "data": series_data
        }]

    return config


def generate_enhanced_visualizations():
    """生成增强的可视化图表配置"""

    # 读取数据
    results_file = "/home/huhuhuhr/code/SQLBot/tmp/analysis_results/all_analysis_results.json"
    with open(results_file, 'r', encoding='utf-8') as f:
        all_results = json.load(f)

    all_charts = []

    # ==================== 1. 执行状态分布（多种图表） ====================
    status_data = all_results["query1_status_distribution"]["data"]

    # 饼图
    all_charts.append(create_chart_config(
        "status_pie", "执行状态分布 - 饼图", "pie", status_data, "执行状态", "任务数量"
    ))

    # 柱状图
    all_charts.append(create_chart_config(
        "status_column", "执行状态分布 - 柱状图", "column", status_data, "执行状态", "任务数量"
    ))

    # 条形图
    all_charts.append(create_chart_config(
        "status_bar", "执行状态分布 - 条形图", "bar", status_data, "执行状态", "任务数量"
    ))

    # 仪表盘（显示成功率）
    success_rate = next((item["占比"] for item in status_data if item["执行状态"] == "执行成功"), 0)
    all_charts.append(create_chart_config(
        "success_gauge", "执行成功率 - 仪表盘", "gauge",
        [{"value": success_rate}], None, "value"
    ))

    # ==================== 2. 任务执行频率 ====================
    task_data = all_results["query2_top_tasks"]["data"]

    if task_data:
        # 柱状图
        all_charts.append(create_chart_config(
            "task_frequency_column", "任务执行频率 - 柱状图", "column", task_data, "任务ID", "执行次数"
        ))

        # 条形图
        all_charts.append(create_chart_config(
            "task_frequency_bar", "任务执行频率 - 条形图", "bar", task_data, "任务名称", "执行次数"
        ))

    # ==================== 3. 触发类型分布 ====================
    trigger_data = all_results["query5_trigger_type"]["data"]

    # 饼图
    all_charts.append(create_chart_config(
        "trigger_pie", "触发类型分布 - 饼图", "pie", trigger_data, "触发类型", "任务数量"
    ))

    # 柱状图
    all_charts.append(create_chart_config(
        "trigger_column", "触发类型分布 - 柱状图", "column", trigger_data, "触发类型", "任务数量"
    ))

    # ==================== 4. 队列分布 ====================
    queue_data = all_results["query6_queue_distribution"]["data"]

    if queue_data:
        # 柱状图
        all_charts.append(create_chart_config(
            "queue_column", "执行队列分布 - 柱状图", "column", queue_data, "队列名称", "任务数量"
        ))

        # 条形图（显示平均耗时）
        all_charts.append(create_chart_config(
            "queue_avg_time_bar", "各队列平均耗时 - 条形图", "bar", queue_data, "队列名称", "平均耗时_秒"
        ))

    # ==================== 5. 状态与耗时关系 ====================
    status_elapsed_data = all_results["query7_status_elapsed"]["data"]

    # 柱状图
    all_charts.append(create_chart_config(
        "status_elapsed_column", "各状态任务数量 - 柱状图", "column", status_elapsed_data, "执行状态", "任务数量"
    ))

    # 条形图（平均耗时）
    all_charts.append(create_chart_config(
        "status_avg_time_bar", "各状态平均耗时 - 条形图", "bar", status_elapsed_data, "执行状态", "平均耗时_秒"
    ))

    # 散点图
    all_charts.append(create_chart_config(
        "status_elapsed_scatter", "状态与耗时关系 - 散点图", "scatter", status_elapsed_data, "任务数量", "平均耗时_秒"
    ))

    # 保存所有图表配置
    output_dir = "/home/huhuhuhr/code/SQLBot/tmp/charts"
    os.makedirs(output_dir, exist_ok=True)

    charts_file = os.path.join(output_dir, "enhanced_charts.json")
    with open(charts_file, 'w', encoding='utf-8') as f:
        json.dump(all_charts, f, ensure_ascii=False, indent=2)

    print(f"✅ 生成了 {len(all_charts)} 个增强图表配置")
    print(f"💾 配置已保存到: {charts_file}")

    return all_charts


if __name__ == "__main__":
    generate_enhanced_visualizations()