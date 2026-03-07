#!/usr/bin/env python3
"""
图表渲染工具 - 将图表配置转换为可执行的图表代码或图片

功能：
1. 生成 ECharts 配置代码（JavaScript）
2. 生成 G2 配置代码（JavaScript）
3. 生成完整 HTML 文件
4. 使用 Python 库生成静态图片（可选）

支持的输出格式：
- echarts-js: ECharts JavaScript 代码
- g2-js: G2 JavaScript 代码
- html: 完整的 HTML 文件
- image: 静态图片（需要安装额外的库）
"""

import json
from typing import Dict, Any, Optional
from pathlib import Path


class ChartRenderer:
    """图表渲染器"""

    @staticmethod
    def render_echarts(config: Dict, data: list, output_id: str = "chart") -> str:
        """
        生成 ECharts JavaScript 代码

        Args:
            config: 图表配置（来自 echarts-renderer SKILL）
            data: 查询结果数据
            output_id: 图表容器 ID

        Returns:
            ECharts JavaScript 代码字符串
        """
        chart_type = config.get("type")
        title = config.get("title", "图表")
        axis = config.get("axis", {})

        # 根据 chart_type 生成不同的 ECharts 配置
        if chart_type == "table":
            return ChartRenderer._render_echarts_table(config, data, output_id)
        elif chart_type == "column":
            return ChartRenderer._render_echarts_column(config, data, output_id)
        elif chart_type == "bar":
            return ChartRenderer._render_echarts_bar(config, data, output_id)
        elif chart_type == "line":
            return ChartRenderer._render_echarts_line(config, data, output_id)
        elif chart_type == "pie":
            return ChartRenderer._render_echarts_pie(config, data, output_id)
        else:
            return f"// 不支持的图表类型: {chart_type}"

    @staticmethod
    def _render_echarts_table(config: Dict, data: list, output_id: str) -> str:
        """生成 ECharts 表格配置"""
        columns = config.get("columns", [])

        # 提取字段和数据
        fields = [col["value"] for col in columns]
        field_names = [col["name"] for col in columns]

        return f'''// ECharts 表格配置
// 需要 echarts 和 echarts-gl 库

const option = {{
  title: {{
    text: '{config.get("title", "数据表格")}',
    left: 'center'
  }},
  tooltip: {{
    trigger: 'axis',
    axisPointer: {{
      type: 'shadow'
    }}
  }},
  dataset: [
    {{
      dimensions: {json.dumps(fields, ensure_ascii=False)},
      source: {json.dumps(data, ensure_ascii=False)}
    }}
  ],
  xAxis: {{ type: 'category' }},
  yAxis: {{ type: 'category' }},
  grid: {{
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  }},
  series: [{{
    type: 'table',
    // 表格配置
  }}]
}};

const chart = echarts.init(document.getElementById('{output_id}'));
chart.setOption(option);
'''

    @staticmethod
    def _render_echarts_column(config: Dict, data: list, output_id: str) -> str:
        """生成 ECharts 柱状图配置"""
        axis = config.get("axis", {})
        x_field = axis["x"]["value"]
        y_field = axis["y"]["value"]
        x_name = axis["x"]["name"]
        y_name = axis["y"]["name"]

        # 提取数据
        x_data = [row[x_field] for row in data]
        y_data = [row[y_field] for row in data]

        # 检查是否有 series
        if "series" in axis:
            # 多系列柱状图
            series_field = axis["series"]["value"]
            series_name = axis["series"]["name"]

            # 按系列分组
            series_groups = {}
            for row in data:
                series_val = row[series_field]
                if series_val not in series_groups:
                    series_groups[series_val] = {"x": [], "y": []}
                series_groups[series_val]["x"].append(row[x_field])
                series_groups[series_val]["y"].append(row[y_field])

            series_config = ",\n    ".join([
        f'{{\n      name: \'{name}\',\n      type: \'bar\',\n      data: {json.dumps(group["y"], ensure_ascii=False)},\n      xAxisIndex: 0,\n      yAxisIndex: 0\n    }}'
        for name, group in series_groups.items()
    ])

            return f'''// ECharts 柱状图配置（多系列）
const option = {{
  title: {{
    text: '{config.get("title", "柱状图")}',
    left: 'center'
  }},
  tooltip: {{
    trigger: 'axis',
    axisPointer: {{
      type: 'shadow'
    }}
  }},
  legend: {{
    data: {list(series_groups.keys())}
  }},
  xAxis: {{
    type: 'category',
    data: {json.dumps(list(set(x_data)), ensure_ascii=False)},
    name: '{x_name}'
  }},
  yAxis: {{
    type: 'value',
    name: '{y_name}'
  }},
  series: [
{series_config}
  ]
}};

const chart = echarts.init(document.getElementById('{output_id}'));
chart.setOption(option);
'''
        else:
            # 单系列柱状图
            return f'''// ECharts 柱状图配置
const option = {{
  title: {{
    text: '{config.get("title", "柱状图")}',
    left: 'center'
  }},
  tooltip: {{
    trigger: 'axis',
    axisPointer: {{
      type: 'shadow'
    }}
  }},
  xAxis: {{
    type: 'category',
    data: {json.dumps(x_data, ensure_ascii=False)},
    name: '{x_name}'
  }},
  yAxis: {{
    type: 'value',
    name: '{y_name}'
  }},
  series: [{{
    name: '{y_name}',
    type: 'bar',
    data: {json.dumps(y_data, ensure_ascii=False)},
    itemStyle: {{
      color: 'params' // 可以根据数值设置不同颜色
    }}
  }}]
}};

const chart = echarts.init(document.getElementById('{output_id}'));
chart.setOption(option);
'''

    @staticmethod
    def _render_echarts_bar(config: Dict, data: list, output_id: str) -> str:
        """生成 ECharts 条形图配置"""
        axis = config.get("axis", {})
        x_field = axis["x"]["value"]
        y_field = axis["y"]["value"]
        x_name = axis["x"]["name"]
        y_name = axis["y"]["name"]

        x_data = [row[x_field] for row in data]
        y_data = [row[y_field] for row in data]

        return f'''// ECharts 条形图配置
const option = {{
  title: {{
    text: '{config.get("title", "条形图")}',
    left: 'center'
  }},
  tooltip: {{
    trigger: 'axis',
    axisPointer: {{
      type: 'shadow'
    }}
  }},
  xAxis: {{
    type: 'value',
    name: '{y_name}',
    data: y_data
  }},
  yAxis: {{
    type: 'category',
    data: x_data,
    name: '{x_name}'
  }},
  series: [{{
    name: '{x_name}',
    type: 'bar',
    data: y_data
  }}]
}};

const chart = echarts.init(document.getElementById('{output_id}'));
chart.setOption(option);
'''

    @staticmethod
    def _render_echarts_line(config: Dict, data: list, output_id: str) -> str:
        """生成 ECharts 折线图配置"""
        axis = config.get("axis", {})
        x_field = axis["x"]["value"]
        y_field = axis["y"]["value"]
        x_name = axis["x"]["name"]
        y_name = axis["y"]["name"]

        x_data = [row[x_field] for row in data]
        y_data = [row[y_field] for row in data]

        # 检查是否有 series
        if "series" in axis:
            # 多系列折线图
            series_field = axis["series"]["value"]

            series_groups = {}
            for row in data:
                series_val = row[series_field]
                if series_val not in series_groups:
                    series_groups[series_val] = {"x": [], "y": []}
                series_groups[series_val]["x"].append(row[x_field])
                series_groups[series_val]["y"].append(row[y_field])

            series_config = ",\n    ".join([
                f"{{ name: '{name}', type: 'line', data: {json.dumps(group['y'], ensure_ascii=False)} }}"
                for name, group in series_groups.items()
            ])

            return f'''// ECharts 折线图配置（多系列）
const option = {{
  title: {{
    text: '{config.get("title", "折线图")}',
    left: 'center'
  }},
  tooltip: {{
    trigger: 'axis'
  }},
  legend: {{
    data: {list(series_groups.keys())}
  }},
  xAxis: {{
    type: 'category',
    data: {json.dumps(list(set(x_data)), ensure_ascii=False)},
    name: '{x_name}'
  }},
  yAxis: {{
    type: 'value',
    name: '{y_name}'
  }},
  series: [
{series_config}
  ]
}};

const chart = echarts.init(document.getElementById('{output_id}'));
chart.setOption(option);
'''
        else:
            # 单系列折线图
            return f'''// ECharts 折线图配置
const option = {{
  title: {{
    text: '{config.get("title", "折线图")}',
    left: 'center'
  }},
  tooltip: {{
    trigger: 'axis'
  }},
  xAxis: {{
    type: 'category',
    data: {json.dumps(x_data, ensure_ascii=False)},
    name: '{x_name}'
  }},
  yAxis: {{
    type: 'value',
    name: '{y_name}'
  }},
  series: [{{
    name: '{y_name}',
    type: 'line',
    data: {json.dumps(y_data, ensure_ascii=False)},
    smooth: true,
    areaStyle: {{}}
  }}]
}};

const chart = echarts.init(document.getElementById('{output_id}'));
chart.setOption(option);
'''

    @staticmethod
    def _render_echarts_pie(config: Dict, data: list, output_id: str) -> str:
        """生成 ECharts 饼图配置"""
        axis = config.get("axis", {})
        y_field = axis["y"]["value"]
        series_field = axis["series"]["value"]
        y_name = axis["y"]["name"]
        series_name = axis["series"]["name"]

        # 提取数据
        pie_data = [
            {"name": row[series_field], "value": row[y_field]}
            for row in data
        ]

        return f'''// ECharts 饼图配置
const option = {{
  title: {{
    text: '{config.get("title", "饼图")}',
    left: 'center'
  }},
  tooltip: {{
    trigger: 'item',
    formatter: '{{{{b}}}: {{{{c}}}} ({{{{d}}}}%)'
  }},
  legend: {{
    orient: 'vertical',
    left: 'left'
  }},
  series: [{{
    name: '{y_name}',
    type: 'pie',
    radius: '50%',
    data: {json.dumps(pie_data, ensure_ascii=False)},
    emphasis: {{
      itemStyle: {{
        shadowBlur: 10,
        shadowOffsetX: 0,
        shadowColor: 'rgba(0, 0, 0, 0.5)'
      }}
    }},
    label: {{
      formatter: '{{{{b}}}: {{{{d}}}}%'
    }}
  }}]
}};

const chart = echarts.init(document.getElementById('{output_id}'));
chart.setOption(option);
'''

    @staticmethod
    def render_g2(config: Dict, data: list, output_id: str = "chart") -> str:
        """
        生成 G2 JavaScript 代码

        Args:
            config: 图表配置（来自 echarts-renderer SKILL）
            data: 查询结果数据
            output_id: 图表容器 ID

        Returns:
            G2 JavaScript 代码字符串
        """
        chart_type = config.get("type")
        axis = config.get("axis", {})

        if chart_type == "column":
            return ChartRenderer._render_g2_column(config, data, output_id)
        elif chart_type == "line":
            return ChartRenderer._render_g2_line(config, data, output_id)
        elif chart_type == "pie":
            return ChartRenderer._render_g2_pie(config, data, output_id)
        else:
            return f"// G2 暂不支持该图表类型: {chart_type}"

    @staticmethod
    def _render_g2_column(config: Dict, data: list, output_id: str) -> str:
        """生成 G2 柱状图配置"""
        axis = config.get("axis", {})
        x_field = axis["x"]["value"]
        y_field = axis["y"]["value"]
        x_name = axis["x"]["name"]
        y_name = axis["y"]["name"]

        return f'''// G2 柱状图配置
const {{ Chart }} = G2;

const chart = new Chart({{
  container: '{output_id}',
  autoFit: true,
  height: 400,
}});

chart
  .interval()
  .data({json.dumps(data, ensure_ascii=False)})
  .encode({{
    x: '{x_field}',
    y: '{y_field}',
    color: '{x_field}',
  }})
  .label({{
    position: 'top',
    style: {{
      fontSize: 12,
    }},
  }})
  .tooltip({{
    title: '{y_name}',
    items: ['{y_name}']
  }})
  .style({{
    fill: '#5B8FF9',
    maxWidth: 20,
  }});

chart.render();
'''

    @staticmethod
    def _render_g2_line(config: Dict, data: list, output_id: str) -> str:
        """生成 G2 折线图配置"""
        axis = config.get("axis", {})
        x_field = axis["x"]["value"]
        y_field = axis["y"]["value"]
        x_name = axis["x"]["name"]
        y_name = axis["y"]["name"]

        return f'''// G2 折线图配置
const {{ Chart }} = G2;

const chart = new Chart({{
  container: '{output_id}',
  autoFit: true,
  height: 400,
}});

chart
  .line()
  .data({json.dumps(data, ensure_ascii=False)})
  .encode({{
    x: '{x_field}',
    y: '{y_field}',
  }})
  .label({{
    style: {{
      stroke: '{y_name}',
      lineWidth: 2,
    }},
  }})
  .tooltip({{
    title: '{x_name}',
    items: ['{y_name}']
  }})
  .style({{
    stroke: '#5B8FF9',
    lineWidth: 2,
  }});

chart.render();
'''

    @staticmethod
    def _render_g2_pie(config: Dict, data: list, output_id: str) -> str:
        """生成 G2 饼图配置"""
        axis = config.get("axis", {})
        y_field = axis["y"]["value"]
        series_field = axis["series"]["value"]
        y_name = axis["y"]["name"]
        series_name = axis["series"]["name"]

        return f'''// G2 饼图配置
const {{ Chart, view }} = G2;

const chart = new Chart({{
  container: '{output_id}',
  autoFit: true,
  height: 400,
}});

chart
  .coordinate({{ type: 'theta' }})
  .interval()
  .data({json.dumps(data, ensure_ascii=False)})
  .transform({{ type: 'stackY' }})
  .encode({{
    y: '{y_field}',
    color: '{series_field}',
  }})
  .label({{
    position: 'outside',
    text: '{series_name}',
    style: {{
      fontSize: 12,
    }},
  }})
  .tooltip({{
    title: '{series_name}',
    items: ['{y_name}']
  }})
  .style({{
    stroke: '#fff',
    lineWidth: 1,
  }});

chart.render();
'''

    @staticmethod
    def render_html(config: Dict, data: list, output_file: str = "chart.html",
                    library: str = "echarts") -> str:
        """
        生成完整的 HTML 文件

        Args:
            config: 图表配置
            data: 查询结果数据
            output_file: 输出文件路径
            library: 使用的库 ('echarts' 或 'g2')

        Returns:
            HTML 文件路径
        """
        chart_id = "chart-container"

        if library == "echarts":
            js_code = ChartRenderer.render_echarts(config, data, chart_id)
        else:
            js_code = ChartRenderer.render_g2(config, data, chart_id)

        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config.get("title", "图表")}</title>
    <script src="https://cdn.jsdelivr.net/npm/{library if library == 'echarts' else '@antv/g2'}@5/dist/{library if library == 'echarts' else 'g2'}.min.js"></script>
</head>
<body>
    <div id="{chart_id}" style="width: 800px; height: 500px; margin: 0 auto;"></div>
    <script type="text/javascript">
{js_code}
    </script>
</body>
</html>'''

        # 写入文件
        output_path = Path(output_file)
        output_path.write_text(html_content, encoding='utf-8')

        return str(output_path.absolute())

    @staticmethod
    def render_python_plotly(config: Dict, data: list, output_file: str = "chart.png"):
        """
        使用 Python plotly 生成静态图片（可选功能）

        Args:
            config: 图表配置
            data: 查询结果数据
            output_file: 输出图片路径

        Returns:
            图片文件路径

        注意：需要安装 plotly 和 kaleido 库：
        pip install plotly kaleido
        """
        try:
            import plotly.graph_objects as go
            import plotly.express as px
        except ImportError:
            return "// 错误：需要安装 plotly 和 kaleido 库\n// pip install plotly kaleido"

        chart_type = config.get("type")
        title = config.get("title", "图表")
        axis = config.get("axis", {})

        if chart_type == "column":
            x_field = axis["x"]["value"]
            y_field = axis["y"]["value"]
            x_name = axis["x"]["name"]
            y_name = axis["y"]["name"]

            x_data = [row[x_field] for row in data]
            y_data = [row[y_field] for row in data]

            fig = go.Figure(data=[go.Bar(
                x=x_data,
                y=y_data,
                name=y_name,
                marker_color='rgb(55, 83, 109)'
            )])

            fig.update_layout(
                title=title,
                xaxis_title=x_name,
                yaxis_title=y_name
            )

        elif chart_type == "line":
            x_field = axis["x"]["value"]
            y_field = axis["y"]["value"]
            x_name = axis["x"]["name"]
            y_name = axis["y"]["name"]

            x_data = [row[x_field] for row in data]
            y_data = [row[y_field] for row in data]

            fig = go.Figure(data=[go.Scatter(
                x=x_data,
                y=y_data,
                mode='lines+markers',
                name=y_name,
                line=dict(color='rgb(55, 83, 109)', width=3)
            )])

            fig.update_layout(
                title=title,
                xaxis_title=x_name,
                yaxis_title=y_name
            )

        elif chart_type == "pie":
            y_field = axis["y"]["value"]
            series_field = axis["series"]["value"]

            labels = [row[series_field] for row in data]
            values = [row[y_field] for row in data]

            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.3,
                textinfo='label+percent',
                textposition='inside'
            )])

            fig.update_layout(title=title)

        else:
            return f"// 暂不支持该图表类型的图片生成: {chart_type}"

        # 保存图片
        output_path = Path(output_file)
        fig.write_image(str(output_path), width=800, height=500, engine='kaleido')

        return str(output_path.absolute())


# CLI 接口
if __name__ == "__main__":
    import sys

    # 示例用法
    if len(sys.argv) > 1:
        import json

        # 读取配置文件
        config_file = sys.argv[1]
        data_file = sys.argv[2] if len(sys.argv) > 2 else None

        if config_file.endswith('.json'):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 读取数据（如果提供）
            data = []
            if data_file and data_file.endswith('.json'):
                with open(data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # 使用示例数据
                data = [
                    {"department": "技术部", "emp_count": 25},
                    {"department": "市场部", "emp_count": 18}
                ]

            # 生成 HTML
            html_file = ChartRenderer.render_html(
                config,
                data,
                output_file="chart_output.html",
                library="echarts"
            )

            print(f"✅ HTML 文件已生成: {html_file}")

            # 尝试生成图片（需要 plotly）
            try:
                img_file = ChartRenderer.render_python_plotly(
                    config,
                    data,
                    output_file="chart_output.png"
                )
                print(f"✅ 图片文件已生成: {img_file}")
            except Exception as e:
                print(f"⚠️  图片生成失败: {e}")
                print("   （如需生成图片，请先安装: pip install plotly kaleido）")
