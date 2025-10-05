# SQLBot OpenAPI 接口文档

## 概述

SQLBot OpenAPI 暴露了认证、数据源管理、对话、推荐以及分析/预测等完整能力。接口遵循 REST 风格并支持服务端推送 (SSE) 以输出长文本和结构化数据。所有接口统一前缀为 "/openapi"，默认交换格式为 "application/json"，流式接口返回 "text/event-stream"。

- 版本: 1.0.0
- 作者: huhuhuhr
- 最近更新: 2025-08-31
- 鉴权: Bearer Token + X-Sqlbot-Token

---

## 使用流程

1. 调用 POST /openapi/getToken 获取访问令牌，可选创建首个聊天。
2. 调用 GET /openapi/getDataSourceList 或 POST /openapi/getDataSourceByIdOrName 确认数据源。
3. 可选：调用 POST /openapi/createRecordAndBindDb 预创建聊天记录并绑定数据源。
4. 调用 POST /openapi/chat 进行对话，接口以 SSE 方式返回推理、SQL、图表与总结。
5. 根据需要调用 POST /openapi/getData、POST /openapi/getRecommend、POST /openapi/analysis、POST /openapi/predict 获取扩展结果。
6. 使用 POST /openapi/deleteChats 清理聊天记录。

     graph TD
        A[获取 Token] --> B[获取或确认数据源]
        B --> C[可选: createRecordAndBindDb]
        C --> D[chat 对话]
        D --> E[getData 获取图表数据]
        D --> F[getRecommend 推荐问题]
        D --> G[analysis / predict]
        E --> H[deleteChats 清理]
        F --> H
        G --> H

---

## 公共请求头

除 POST /openapi/getToken 以外的接口均需在请求头中携带下列字段：

    Authorization: Bearer <access_token>
    X-Sqlbot-Token: <access_token>
    Content-Type: application/json

流式接口响应头额外包含 Content-Type: text/event-stream。

---

## 接口一览

| # | 方法 | 路径 | 说明 | 响应模式 |
|---|------|------------------------------|----------------------------------|------------|
| 1 | POST | /openapi/getToken | 获取访问令牌，可选创建聊天 | JSON |
| 2 | GET  | /openapi/getDataSourceList | 获取可访问数据源列表 | JSON |
| 3 | POST | /openapi/getDataSourceByIdOrName | 通过 ID 或名称查询数据源 | JSON |
| 4 | POST | /openapi/createRecordAndBindDb | 创建聊天记录并绑定数据源 | JSON |
| 5 | POST | /openapi/chat | 执行数据库对话 (自动生成 SQL 与图表) | SSE |
| 6 | POST | /openapi/getData | 获取聊天生成的图表数据 | JSON |
| 7 | POST | /openapi/getRecommend | 生成推荐问题 | SSE |
| 8 | POST | /openapi/deleteChats | 批量或全部清理聊天 | JSON |
| 9 | POST | /openapi/analysis | 基于记录进行分析 | SSE |
| 10 | POST | /openapi/predict | 基于记录进行预测 | SSE |

---
## 接口详情

### 1. 获取访问令牌 POST /openapi/getToken

请求体示例:

    {
        "username": "demo",
        "password": "***",
        "create_chat": false
    }

响应示例:

    {
        "access_token": "bearer eyJ...",
        "token_type": "bearer",
        "expire": "2025-01-30 15:30:00",
        "chat_id": 123
    }

错误码: 400 (账号或工作空间异常)。

---

### 2. 获取数据源列表 GET /openapi/getDataSourceList

- 需要携带认证头。
- 返回当前用户工作空间内可访问的数据源数组。

---

### 3. 根据 ID 或名称获取数据源 POST /openapi/getDataSourceByIdOrName

请求体 (name 与 id 至少提供一个):

    {
        "name": "sales_ds",
        "id": 12
    }

验证失败会返回 400, 提示 name 和 id 不能同时为空。

---

### 4. 创建聊天并绑定数据源 POST /openapi/createRecordAndBindDb

请求体:

    {
        "title": "销售看板",
        "db_id": 12,
        "origin": 0
    }

返回值: 新建聊天记录对象; 发生异常时返回 500。

---

### 5. 聊天接口 POST /openapi/chat

请求体字段说明:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question | string | 是 | 用户问题文本 |
| chat_id | integer | 是 | 聊天会话 ID |
| db_id | integer | 是 | 数据源 ID |
| my_sql | string | 否 | 自定义 SQL, 非空时直接执行 |
| my_promote | string | 否 | 自定义系统提示词, 支持 Template 变量 |
| my_schema | string | 否 | 手工提供 schema 信息 |
| intent | boolean | 否 | 是否启用意图识别, 默认 false |
| analysis | boolean | 否 | 是否在结束后执行分析 |
| predict | boolean | 否 | 是否在结束后执行预测 |
| recommend | boolean | 否 | 是否追加推荐问题 |
| every | boolean | 否 | 分析阶段是否逐条处理数据 |
| no_reasoning | boolean | 否 | 是否关闭模型思考, 默认 true |
| history_open | boolean | 否 | 是否带入历史消息, 默认 true |

SSE 流常见 type:

| type | 含义 |
|------|------|
| id | 当前聊天记录 ID |
| brief | 自动生成的聊天标题 |
| datasource / datasource-result | 动态数据源选择过程 |
| sql-result | SQL 生成阶段的增量内容 |
| chart-result | 图表生成过程描述 |
| chart-data | get_chat_chart_data 的结果 (JSON 字符串) |
| data-finish | 图表数据推送完成, 内容为记录 ID |
| analysis-result / predict-result | 衍生分析或预测阶段输出 |
| analysis_finish / predict_finish | 对应阶段结束标记 |
| recommended_question | 推荐问题 (recommend 为 true 时出现) |
| warning | 非致命问题提示 (例如聊天记录不存在) |
| error | 处理异常, 内容包含错误信息 |
| finish | 主对话流程结束 |

若绑定的数据源不存在或无权限, 接口返回 500。

---

### 6. 获取聊天图表数据 POST /openapi/getData

请求体:

    {
        "chat_record_id": 456
    }

返回 get_chat_chart_data 的结果, 包含 chart、data、columns 等字段。

---

### 7. 推荐问题 POST /openapi/getRecommend

请求体:

    {
        "chat_record_id": 456,
        "chat_id": 123
    }

响应为 SSE 流, type 包括 recommended_question 和 recommended_question_result。记录不存在时返回 400。

---

### 8. 清理聊天 POST /openapi/deleteChats

请求体:

    {
        "chat_ids": [1, 2, 3]
    }

chat_ids 可为空表示清理全部。返回示例:

    {
        "message": "清理完成, 总共 3 条记录, 成功 3 条, 失败 0 条",
        "success_count": 3,
        "failed_count": 0,
        "total_count": 3
    }

---

### 9. 分析接口 POST /openapi/analysis

请求体示例:

    {
        "chat_record_id": 456,
        "chat_id": 123,
        "question": "请按地区对销售额进行对比",
        "my_promote": null,
        "my_schema": null,
        "every": false,
        "history_open": true,
        "no_reasoning": false,
        "intent": true
    }

若提供 chat_record_id, 需保证记录已生成图表数据; 否则返回 500。响应流包含 analysis-result、analysis_finish、error 等类型。传入 chat_data_object 时服务端会构建临时 ChatRecord 进行分析。

---

### 10. 预测接口 POST /openapi/predict

请求体与分析接口一致, 区别在于执行预测。响应流包括 predict-result、predict-success、predict-failed、predict_finish 等事件。

---
## 流式数据处理提示

1. 使用支持 SSE 的客户端 (浏览器 EventSource、Python requests.iter_lines 等) 持续读取以 data: 开头的行。
2. 去除 data: 前缀后再解析 JSON。
3. 收到 finish、analysis_finish 或 predict_finish 表示对应阶段完成，可按业务需求决定是否继续监听其他阶段。
4. warning 类型表示非致命警告 (如聊天记录已清理)，可提示用户或忽略等待后续事件。

---

## 调用示例 (Python)

    import requests

    BASE = "http://localhost:8000"

    resp = requests.post(f"{BASE}/openapi/getToken", json={
        "username": "demo",
        "password": "demo",
        "create_chat": True
    })
    resp.raise_for_status()
    token_info = resp.json()
    access_token = token_info["access_token"].split(" ", 1)[1]
    chat_id = token_info.get("chat_id")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Sqlbot-Token": access_token,
        "Content-Type": "application/json"
    }

    resp = requests.get(f"{BASE}/openapi/getDataSourceList", headers=headers)
    resp.raise_for_status()
    datasource_id = resp.json()[0]["id"]

    chat_req = {
        "question": "请统计 2024 年每月销售额",
        "chat_id": chat_id,
        "db_id": datasource_id,
        "intent": True,
        "analysis": True
    }

    with requests.post(f"{BASE}/openapi/chat", headers=headers, json=chat_req, stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            payload = line.decode().removeprefix("data:")
            print(payload)
            if '"type":"finish"' in payload:
                break

    resp = requests.post(f"{BASE}/openapi/getData", headers=headers, json={
        "chat_record_id": chat_id
    })
    resp.raise_for_status()
    print(resp.json())

---

## 常见问题

- 数据源绑定失败: 请确认 db_id 属于当前令牌用户的工作空间。
- SSE 连接被断开: 检查反向代理超时配置, 必要时实现客户端重连。
- 关闭模型思考: 在请求体中设置 no_reasoning 为 true。

更多字段验证规则可参考 backend/apps/openapi/models/openapiModels.py。
