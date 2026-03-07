#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 execution_records 表多维度分析报告 PDF
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import json
import os
from datetime import datetime

# 注册中文字体（尝试使用系统字体）
def register_chinese_font():
    """注册中文字体"""
    font_configs = [
        ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 'Noto Sans CJK SC', 'NotoSansCJK'),
        ('/usr/share/fonts/truetype/arphic/uming.ttc', 'AR PL UMing TW MBE', 'ARPLUMing'),
        ('/usr/share/fonts/truetype/arphic/ukai.ttc', 'AR PL UKai CN', 'ARPLUKai'),
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',  # 文泉驿正黑
        '/System/Library/Fonts/PingFang.ttc',  # macOS PingFang
        'C:/Windows/Fonts/msyh.ttc',  # Windows 微软雅黑
    ]

    for font_config in font_configs:
        if isinstance(font_config, tuple):
            font_path, font_name, font_alias = font_config
        else:
            font_path = font_config
            font_name = 'ChineseFont'
            font_alias = 'ChineseFont'

        if os.path.exists(font_path):
            try:
                # 对于 TTC 文件，需要指定子字体索引
                if font_path.endswith('.ttc'):
                    pdfmetrics.registerFont(TTFont(font_alias, font_path, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont(font_alias, font_path))
                print(f"✅ 注册字体: {font_name} from {font_path}")
                return font_alias
            except Exception as e:
                print(f"⚠️  无法注册字体 {font_path}: {e}")
                continue

    print("❌ 无法找到可用的中文字体")
    return None

# 创建样式
def create_styles(chinese_font=None):
    """创建文档样式"""
    styles = getSampleStyleSheet()

    if chinese_font:
        # 使用中文字体
        styles.add(ParagraphStyle(
            name='ChineseTitle',
            parent=styles['Heading1'],
            fontName=chinese_font,
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        styles.add(ParagraphStyle(
            name='ChineseHeading2',
            parent=styles['Heading2'],
            fontName=chinese_font,
            fontSize=18,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12
        ))
        styles.add(ParagraphStyle(
            name='ChineseHeading3',
            parent=styles['Heading3'],
            fontName=chinese_font,
            fontSize=14,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=10
        ))
        styles.add(ParagraphStyle(
            name='ChineseNormal',
            parent=styles['Normal'],
            fontName=chinese_font,
            fontSize=10,
            leading=14
        ))
        styles.add(ParagraphStyle(
            name='ChineseSmall',
            parent=styles['Normal'],
            fontName=chinese_font,
            fontSize=9,
            leading=12
        ))
    else:
        # 使用默认字体
        styles.add(ParagraphStyle(
            name='ChineseTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            alignment=TA_CENTER,
            spaceAfter=20
        ))
        styles.add(ParagraphStyle(
            name='ChineseHeading2',
            parent=styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=12
        ))
        styles.add(ParagraphStyle(
            name='ChineseHeading3',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#7f8c8d'),
            spaceAfter=10
        ))

    return styles

# 创建数据表格
def create_data_table(data, styles, chinese_font=None):
    """创建数据表格"""
    if not data:
        return Paragraph("No data available", styles['ChineseNormal'])

    # 获取表头
    headers = list(data[0].keys())

    # 构建表格数据
    table_data = [headers]  # 表头
    for row in data[:10]:  # 最多显示 10 行
        table_data.append([str(row.get(h, '')) for h in headers])

    # 创建表格
    table = Table(table_data, repeatRows=1)

    # 设置表格样式
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), chinese_font or 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), chinese_font or 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
    ]))

    return table

# 生成报告
def generate_report():
    """生成完整的分析报告"""

    # 注册字体
    chinese_font = register_chinese_font()

    # 创建输出文件
    output_file = "/home/huhuhuhr/code/SQLBot/tmp/execution_records_analysis_report.pdf"
    doc = SimpleDocTemplate(output_file, pagesize=A4)
    styles = create_styles(chinese_font)

    story = []

    # 读取数据
    results_file = "/home/huhuhuhr/code/SQLBot/tmp/analysis_results/all_analysis_results.json"
    charts_file = "/home/huhuhuhr/code/SQLBot/tmp/charts/all_charts.json"

    with open(results_file, 'r', encoding='utf-8') as f:
        all_results = json.load(f)
    with open(charts_file, 'r', encoding='utf-8') as f:
        all_charts = json.load(f)

    # ==================== 标题页 ====================
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph("execution_records 表", styles['ChineseTitle']))
    story.append(Paragraph("多维度分析报告", styles['ChineseTitle']))
    story.append(Spacer(1, 2*cm))

    # 数据库信息
    info_data = [
        ['数据库:', 'dix_scheduler'],
        ['主机:', 'localhost:17082'],
        ['Schema:', 'public'],
        ['总记录数:', '53'],
        ['分析维度:', '7'],
        ['生成时间:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    ]

    info_table = Table(info_data, colWidths=[4*cm, 6*cm])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), chinese_font or 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 2*cm))

    # ==================== 分析概览 ====================
    story.append(Paragraph("分析概览", styles['ChineseHeading2']))
    story.append(Spacer(1, 0.5*cm))

    overview_text = """
    本报告对 execution_records 表进行了全面的多维度分析，涵盖执行状态分布、任务频率、
    耗时统计、趋势分析、触发类型、队列分布和状态与耗时关系等 7 个维度。
    分析基于 PostgreSQL 数据库，共处理 53 条执行记录。
    """

    story.append(Paragraph(overview_text, styles['ChineseNormal']))
    story.append(Spacer(1, 1*cm))
    story.append(PageBreak())

    # ==================== 7 个分析章节 ====================
    analysis_info = [
        {
            "key": "query1_status_distribution",
            "title": "1. 执行状态分布分析",
            "description": "统计各个执行状态的任务数量和占比"
        },
        {
            "key": "query2_top_tasks",
            "title": "2. 任务执行频率 TOP 10",
            "description": "按 task_id 统计执行次数最多的前10个任务"
        },
        {
            "key": "query3_elapsed_time_stats",
            "title": "3. 执行耗时统计分析",
            "description": "计算所有任务的平均耗时、最大耗时、最小耗时、中位数耗时"
        },
        {
            "key": "query4_daily_trend",
            "title": "4. 每日执行趋势分析",
            "description": "按日期统计任务执行数量和平均耗时"
        },
        {
            "key": "query5_trigger_type",
            "title": "5. 触发类型分布分析",
            "description": "统计不同触发类型的任务数量和占比"
        },
        {
            "key": "query6_queue_distribution",
            "title": "6. 执行队列分布分析",
            "description": "统计各执行队列的任务数量和平均耗时"
        },
        {
            "key": "query7_status_elapsed",
            "title": "7. 任务状态与耗时关系分析",
            "description": "分析不同状态下的平均耗时"
        }
    ]

    for info in analysis_info:
        key = info["key"]

        # 章节标题
        story.append(Paragraph(info["title"], styles['ChineseHeading2']))
        story.append(Spacer(1, 0.3*cm))

        # 描述
        story.append(Paragraph(f"<b>分析目的:</b> {info['description']}", styles['ChineseNormal']))
        story.append(Spacer(1, 0.5*cm))

        # 图表类型
        chart = next((c for c in all_charts if key in c.get("title", "")), None)
        if chart:
            chart_type = chart.get("type", "unknown")
            chart_type_map = {
                "pie": "饼图",
                "column": "柱状图",
                "bar": "条形图",
                "line": "折线图",
                "table": "数据表"
            }
            story.append(Paragraph(f"<b>推荐图表:</b> {chart_type_map.get(chart_type, chart_type)}", styles['ChineseNormal']))
            story.append(Spacer(1, 0.3*cm))

        # SQL 查询
        if chart and chart.get("sql"):
            story.append(Paragraph("<b>SQL 查询:</b>", styles['ChineseHeading3']))
            sql_text = chart["sql"].replace("\n", " ")
            if len(sql_text) > 100:
                sql_text = sql_text[:100] + "..."
            story.append(Paragraph(f"<font name='Courier'>{sql_text}</font>", styles['ChineseSmall']))
            story.append(Spacer(1, 0.5*cm))

        # 数据表格
        result = all_results.get(key)
        if result and result.get("success"):
            data = result.get("data", [])
            story.append(Paragraph("<b>分析结果:</b>", styles['ChineseHeading3']))
            story.append(Spacer(1, 0.2*cm))

            if data:
                table = create_data_table(data, styles, chinese_font)
                story.append(table)
            else:
                story.append(Paragraph("无数据", styles['ChineseNormal']))

        story.append(Spacer(1, 1*cm))

        # 每 3 个分析换页
        if analysis_info.index(info) in [2, 5]:
            story.append(PageBreak())

    # ==================== 总结 ====================
    story.append(PageBreak())
    story.append(Paragraph("分析总结", styles['ChineseHeading2']))
    story.append(Spacer(1, 0.5*cm))

    summary_points = [
        "1. 执行成功率: 98.11% (52/53)，任务执行稳定性良好",
        "2. 主要任务: stream_test 任务占全部执行记录的 100%",
        "3. 耗时情况: 当前数据中所有任务耗时均为 0，需检查数据采集逻辑",
        "4. 触发方式: 所有任务均通过 CRON 定时触发",
        "5. 队列分配: 所有任务都在 fast 队列中执行",
        "6. 时间分布: 所有任务集中在 2026-01-14 执行"
    ]

    for point in summary_points:
        story.append(Paragraph(f"• {point}", styles['ChineseNormal']))
        story.append(Spacer(1, 0.3*cm))

    # 建议
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph("优化建议", styles['ChineseHeading2']))
    story.append(Spacer(1, 0.3*cm))

    recommendations = [
        "1. 检查 elapsed_time 字段的数据采集逻辑，确保正确记录任务执行耗时",
        "2. 增加更多样化的任务类型，避免单一任务占用所有资源",
        "3. 考虑使用多个执行队列，实现更好的任务隔离和负载均衡",
        "4. 添加任务失败重试机制，提高系统容错能力",
        "5. 建立任务性能监控告警，及时发现异常耗时任务"
    ]

    for rec in recommendations:
        story.append(Paragraph(f"• {rec}", styles['ChineseNormal']))
        story.append(Spacer(1, 0.3*cm))

    # 页脚
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph(
        f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  "
        f"数据库: dix_scheduler@localhost:17082  |  "
        f"工具: SQLBot Analysis System",
        styles['ChineseSmall']
    ))

    # 构建 PDF
    doc.build(story)

    print(f"✅ PDF 报告生成成功: {output_file}")
    return output_file

if __name__ == "__main__":
    generate_report()