#!/usr/bin/env python3
"""
数据转换工具 - 将 SQL 查询结果转换为图表配置

功能：
1. 解析 SQL 查询结构
2. 检测字段类型（维度/指标）
3. 根据图表类型映射字段到轴
4. 生成图表配置 JSON
"""

import re
from typing import Dict, List, Any, Optional
from datetime import datetime


class DataType:
    """字段类型枚举"""
    DIMENSION = "dimension"  # 维度字段（分类、时间）
    METRIC = "metric"      # 指标字段（数值）


class FieldInfo:
    """字段信息"""
    def __init__(self, name: str, alias: Optional[str] = None, data_type: Optional[str] = None):
        self.name = name          # 原始字段名
        self.alias = alias        # 别名
        self.data_type = data_type  # SQL 数据类型
        self.field_type = None    # dimension 或 metric
        self.sample_values = []   # 样本值

    @property
    def display_name(self) -> str:
        """获取显示名称（优先使用别名）"""
        return self.alias or self.name

    @property
    def safe_name(self) -> str:
        """获取安全名称（去掉引号）"""
        name = self.display_name
        # 去掉各种引号
        name = re.sub(r'^["`\[]+|["`\]]+$', '', name)
        return name


class SQLAnalyzer:
    """SQL 查询分析器"""

    # 聚合函数模式
    AGGREGATION_PATTERNS = [
        r'COUNT\s*\(',
        r'SUM\s*\(',
        r'AVG\s*\(',
        r'MIN\s*\(',
        r'MAX\s*\(',
    ]

    @staticmethod
    def extract_columns(sql: str) -> List[FieldInfo]:
        """提取 SELECT 列信息"""
        # 提取 SELECT 和 FROM 之间的部分
        match = re.search(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
        if not match:
            return []

        select_clause = match.group(1)
        columns = []

        # 分割列（考虑逗号，但要忽略函数内的逗号）
        # 简化处理：按逗号分割
        for col in select_clause.split(','):
            col = col.strip()

            # 解析字段名和别名
            # 格式：column_name AS alias 或 column_name alias
            alias_match = re.search(r'AS\s+([^\s]+)$', col, re.IGNORECASE)
            if alias_match:
                field_name = re.sub(r'\s+AS\s+.*$', '', col, flags=re.IGNORECASE).strip()
                alias = alias_match.group(1).strip('"\`[]')
            else:
                # 尝试匹配 "column_name alias" 格式
                parts = col.split()
                if len(parts) >= 2:
                    field_name = parts[0].strip()
                    alias = parts[-1].strip('"\`[]')
                else:
                    field_name = col.strip()
                    alias = None

            # 去掉表名前缀（table.column）
            if '.' in field_name:
                field_name = field_name.split('.')[-1]

            field_name = field_name.strip('"\`[]')

            columns.append(FieldInfo(field_name, alias))

        return columns

    @staticmethod
    def detect_aggregations(columns: List[FieldInfo], sql: str) -> List[str]:
        """检测聚合函数字段"""
        aggregated = []

        for pattern in SQLAnalyzer.AGGREGATION_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                # 找到包含聚合函数的字段
                for col in columns:
                    if re.search(pattern, sql[sql.lower().find(col.name.lower()):], re.IGNORECASE):
                        aggregated.append(col.display_name)

        return aggregated

    @staticmethod
    def extract_group_by(sql: str) -> List[str]:
        """提取 GROUP BY 字段"""
        match = re.search(r'GROUP BY\s+(.+?)(?:ORDER BY|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if not match:
            return []

        group_by_clause = match.group(1).strip()
        fields = []

        for field in group_by_clause.split(','):
            field = field.strip()
            # 去掉表名前缀和引号
            field = re.sub(r'^.*\.', '', field)
            field = field.strip('"\`[]')
            fields.append(field)

        return fields


class DataTypeDetector:
    """数据类型检测器"""

    @staticmethod
    def detect_field_types(columns: List[FieldInfo], data: List[Dict], group_by: List[str], aggregations: List[str]):
        """
        检测字段类型

        规则：
        1. GROUP BY 字段 → 维度
        2. 聚合函数字段 → 指标
        3. 数值类型 → 指标
        4. 时间类型 → 维度
        5. 字符串类型（低基数） → 维度
        """
        if not data:
            return

        for col in columns:
            # 规则 1: GROUP BY 字段
            if col.name in group_by or col.display_name in group_by:
                col.field_type = DataType.DIMENSION
                continue

            # 规则 2: 聚合函数字段
            if col.display_name in aggregations:
                col.field_type = DataType.METRIC
                continue

            # 规则 3-5: 基于数据类型和样本值判断
            if data:
                sample_value = data[0].get(col.display_name) or data[0].get(col.name)

                if sample_value is None:
                    continue

                # 数值类型 → 指标
                if isinstance(sample_value, (int, float)):
                    col.field_type = DataType.METRIC

                # 时间类型 → 维度
                elif isinstance(sample_value, str):
                    # 检查是否为时间格式
                    time_patterns = [
                        r'\d{4}-\d{2}-\d{2}',           # YYYY-MM-DD
                        r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',  # YYYY-MM-DD HH:MM:SS
                        r'\d{4}-\d{2}',                # YYYY-MM
                        r'\d{4}',                       # YYYY
                    ]
                    if any(re.match(pattern, sample_value) for pattern in time_patterns):
                        col.field_type = DataType.DIMENSION
                    else:
                        # 字符串类型 → 根据基数判断
                        unique_values = set()
                        for row in data[:100]:  # 最多检查100行
                            val = row.get(col.display_name) or row.get(col.name)
                            if val is not None:
                                unique_values.add(str(val))
                            if len(unique_values) > 50:
                                break

                        # 基数 < 50 → 维度
                        if len(unique_values) < 50:
                            col.field_type = DataType.DIMENSION
                        else:
                            # 高基数字符串，可能是 ID → 维度
                            col.field_type = DataType.DIMENSION


class ChartConfigGenerator:
    """图表配置生成器"""

    @staticmethod
    def generate_table_config(columns: List[FieldInfo], title: str) -> Dict:
        """生成表格配置"""
        return {
            "type": "table",
            "title": title,
            "columns": [
                {
                    "name": col.display_name,  # 使用中文名称（如果有）
                    "value": col.safe_name
                }
                for col in columns
            ]
        }

    @staticmethod
    def generate_xy_config(chart_type: str, columns: List[FieldInfo], title: str) -> Dict:
        """
        生成 X-Y 图表配置（column/bar/line）

        字段映射规则：
        - X 轴：维度字段（优先 GROUP BY 字段）
        - Y 轴：指标字段（优先聚合字段）
        - Series：可选的第二维度字段
        """
        dimensions = [col for col in columns if col.field_type == DataType.DIMENSION]
        metrics = [col for col in columns if col.field_type == DataType.METRIC]

        if not dimensions or not metrics:
            return {
                "type": "error",
                "reason": f"无法生成{chart_type}图表：缺少维度字段或指标字段"
            }

        # 选择 X 轴（第一个维度）
        x_field = dimensions[0]
        # 选择 Y 轴（第一个指标）
        y_field = metrics[0]

        config = {
            "type": chart_type,
            "title": title,
            "axis": {
                "x": {
                    "name": x_field.display_name,
                    "value": x_field.safe_name
                },
                "y": {
                    "name": y_field.display_name,
                    "value": y_field.safe_name
                }
            }
        }

        # 如果有第二个维度，添加为 series
        if len(dimensions) > 1:
            config["axis"]["series"] = {
                "name": dimensions[1].display_name,
                "value": dimensions[1].safe_name
            }

        return config

    @staticmethod
    def generate_pie_config(columns: List[FieldInfo], title: str) -> Dict:
        """
        生成饼图配置

        字段映射规则：
        - Y 轴：指标字段（数值大小）
        - Series：维度字段（分类）
        """
        dimensions = [col for col in columns if col.field_type == DataType.DIMENSION]
        metrics = [col for col in columns if col.field_type == DataType.METRIC]

        if not dimensions or not metrics:
            return {
                "type": "error",
                "reason": "无法生成饼图：缺少维度字段或指标字段"
            }

        return {
            "type": "pie",
            "title": title,
            "axis": {
                "y": {
                    "name": metrics[0].display_name,
                    "value": metrics[0].safe_name
                },
                "series": {
                    "name": dimensions[0].display_name,
                    "value": dimensions[0].safe_name
                }
            }
        }


def convert_to_chart_config(
    sql: str,
    data: List[Dict],
    chart_type: str,
    question: str = ""
) -> Dict:
    """
    主函数：将 SQL 查询结果转换为图表配置

    Args:
        sql: SQL 查询语句
        data: 查询结果数据
        chart_type: 图表类型（table/column/bar/line/pie）
        question: 用户问题（用于生成标题）

    Returns:
        图表配置字典
    """
    # 步骤 1: 分析 SQL 结构
    columns = SQLAnalyzer.extract_columns(sql)
    group_by_fields = SQLAnalyzer.extract_group_by(sql)
    aggregations = SQLAnalyzer.detect_aggregations(columns, sql)

    # 步骤 2: 检测字段类型
    DataTypeDetector.detect_field_types(columns, data, group_by_fields, aggregations)

    # 步骤 3: 生成标题（如果未提供）
    title = question or "数据图表"
    if len(title) > 20:
        title = title[:20] + "..."

    # 步骤 4: 根据图表类型生成配置
    if chart_type == "table":
        return ChartConfigGenerator.generate_table_config(columns, title)

    elif chart_type in ["column", "bar", "line"]:
        return ChartConfigGenerator.generate_xy_config(chart_type, columns, title)

    elif chart_type == "pie":
        return ChartConfigGenerator.generate_pie_config(columns, title)

    else:
        return {
            "type": "error",
            "reason": f"不支持的图表类型：{chart_type}"
        }


# CLI 接口
if __name__ == "__main__":
    import sys
    import json

    # 示例用法
    if len(sys.argv) > 1:
        sql = sys.argv[1]
        chart_type = sys.argv[2] if len(sys.argv) > 2 else "table"

        # 示例数据（实际应该从数据库查询）
        example_data = [
            {"department": "技术部", "emp_count": 25},
            {"department": "市场部", "emp_count": 18},
            {"department": "人事部", "emp_count": 8}
        ]

        config = convert_to_chart_config(
            sql=sql,
            data=example_data,
            chart_type=chart_type,
            question="部门人数统计"
        )

        print(json.dumps(config, ensure_ascii=False, indent=2))
