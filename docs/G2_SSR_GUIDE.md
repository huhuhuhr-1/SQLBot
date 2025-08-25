# G2-SSR 图表渲染服务说明

## 📊 什么是 G2-SSR？

G2-SSR (G2 Server-Side Rendering) 是 SQLBot 项目中的图表服务端渲染服务，主要负责将数据转换为图片格式的图表。

## 🎯 主要作用

### 1. 图表图片生成
- 将查询结果数据转换为可视化图表
- 支持多种图表类型：柱状图、折线图、饼图、条形图
- 生成 PNG 格式的图片文件

### 2. 服务端渲染
- 在服务器端生成图表，不依赖浏览器环境
- 确保图表在不同环境下的一致性
- 支持批量图表生成

### 3. 数据可视化
- 将 SQL 查询结果转换为直观的图表
- 支持自定义图表样式和主题
- 提供图表导出功能

## 🔧 技术实现

### 核心依赖
```json
{
  "@antv/g2": "^5.3.3",        // 图表库
  "@antv/g2-ssr": "^0.1.0",    // 服务端渲染库
  "node-canvas": "^2.9.0"      // Canvas 渲染引擎
}
```

### 服务架构
```
g2-ssr/
├── app.js              # 主服务文件
├── charts/             # 图表配置
│   ├── bar.js         # 条形图配置
│   ├── column.js      # 柱状图配置
│   ├── line.js        # 折线图配置
│   ├── pie.js         # 饼图配置
│   └── utils.js       # 工具函数
└── package.json       # 依赖配置
```

### 工作流程
1. **接收请求**: 接收来自后端的图表生成请求
2. **解析数据**: 解析图表类型、坐标轴配置、数据
3. **生成配置**: 根据图表类型生成 G2 配置
4. **渲染图表**: 使用 G2-SSR 渲染图表
5. **导出图片**: 将图表导出为 PNG 文件

## 📈 支持的图表类型

### 1. 柱状图 (Column)
- 适用于分类数据对比
- 支持多系列数据
- 可自定义颜色和样式

### 2. 折线图 (Line)
- 适用于趋势分析
- 支持时间序列数据
- 可显示数据变化趋势

### 3. 饼图 (Pie)
- 适用于占比分析
- 支持百分比显示
- 可自定义标签位置

### 4. 条形图 (Bar)
- 适用于排名对比
- 支持水平布局
- 适合长标签显示

## 🚀 使用方式

### API 调用
```bash
# POST 请求到 g2-ssr 服务
curl -X POST http://localhost:3000 \
  -H "Content-Type: application/json" \
  -d '{
    "type": "column",
    "axis": "{\"x\": \"category\", \"y\": \"value\"}",
    "data": "[{\"category\": \"A\", \"value\": 10}, {\"category\": \"B\", \"value\": 20}]",
    "path": "/tmp/chart.png"
  }'
```

### 请求参数
```json
{
  "type": "chart_type",        // 图表类型: bar, column, line, pie
  "axis": "axis_config",       // 坐标轴配置 (JSON 字符串)
  "data": "chart_data",        // 图表数据 (JSON 字符串)
  "path": "output_path"        // 输出文件路径 (可选)
}
```

### 响应结果
- 成功: 返回 "complete" 并生成图片文件
- 失败: 返回错误信息

## 🔍 在 SQLBot 中的应用

### 1. 查询结果可视化
- 用户通过自然语言查询数据
- 系统自动选择合适的图表类型
- 调用 g2-ssr 服务生成图表

### 2. 报告生成
- 支持批量图表生成
- 可嵌入到报告中
- 提供图片下载功能

### 3. 数据分享
- 生成独立的图片文件
- 支持邮件发送
- 可保存到文件系统

## 🛠️ 开发调试

### 启动服务
```bash
cd g2-ssr
npm install
npm start
```

### 测试图表生成
```bash
# 测试柱状图
curl -X POST http://localhost:3000 \
  -H "Content-Type: application/json" \
  -d '{
    "type": "column",
    "axis": "{\"x\": \"month\", \"y\": \"sales\"}",
    "data": "[{\"month\": \"Jan\", \"sales\": 100}, {\"month\": \"Feb\", \"sales\": 200}]"
  }'
```

### 常见问题
1. **Canvas 依赖**: 确保系统安装了 Canvas 相关依赖
2. **内存使用**: 大量图表生成时注意内存使用
3. **并发处理**: 服务支持并发请求处理

## 📚 相关文档

- [G2 官方文档](https://g2.antv.vision/)
- [G2-SSR 文档](https://github.com/antvis/g2-ssr)
- [Node-Canvas 文档](https://github.com/Automattic/node-canvas)

---

G2-SSR 服务是 SQLBot 数据可视化功能的核心组件，为用户提供了强大的图表生成能力。
