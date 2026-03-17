# 深度分析模块 - 复杂数据探查能力改造计划

**创建时间**: 2026-03-15 22:45  
**改造目标**: 让深度分析模块输出完整的"证据链"，支持复杂数据探查  
**预计工时**: 2.5 小时

---

## 一、改造背景

### 1.1 业务需求

用户需要用自然语言提出**复杂数据分析问题**，例如：

> "请分析最近 7 天高风险登录事件，按设备类型统计异常次数，并给出 Top10 用户。"

这类问题需要：

1. **多步骤执行**：过滤 → 分组 → 排序（不能单查询完成）
2. **过程可追溯**：用户需要知道结论是怎么来的
3. **证据可验证**：每个分析步骤都要有数据支撑

### 1.2 现状

深度分析模块（`apps/openapi/agent/`）已具备：

- ✅ PlanAgent - Agent 编排框架
- ✅ GetDataTool - 智能取数工具
- ✅ InsightTool - 7 种数据分析算法
- ✅ SaveInsightTool - 保存分析洞察
- ✅ FinalAnswerTool - 输出最终答案

### 1.3 核心问题

**问题 1：查询步骤没有记录**

- 现状：Agent 执行了多步查询，但不知道每步查了什么
- 影响：无法追溯分析过程，用户不知道结论从哪来

**问题 2：证据没有结构化**

- 现状：`AnalysisContext.insights` 只存了 `{"data": df, "insight": "xxx"}`
- 影响：数据和分析过程没有关联，无法验证

**问题 3：最终结果没有统一格式**

- 现状：FinalAnswerTool 只返回一句话结论
- 影响：前端无法展示完整的证据链

---

## 二、改造目标

### 2.1 核心目标

让深度分析模块在分析结束后输出**结构化结果包（RPACK）**：

```json
{
  "conclusion": "最终结论",
  "evidence": [
    {
      "query_id": "q1",
      "insight": "OutstandingFirst",
      "analysis_process": "分析过程描述",
      "data_summary": {
        "row_count": 100,
        "columns": [
          "a",
          "b"
        ]
      }
    }
  ],
  "query_chain": [
    {
      "query_id": "q1",
      "query": "查询描述",
      "sql": "SELECT...",
      "status": "completed"
    }
  ],
  "total_steps": 3
}
```

### 2.2 不改什么（本期范围外）

- ❌ 语义版本管理（以后再说）
- ❌ DAG 可视化（可选增强）
- ❌ 超时控制（可选增强）
- ❌ 性能优化（后续迭代）

---

## 三、改造范围

| 文件                                                      | 改造内容                      | 优先级 |
|---------------------------------------------------------|---------------------------|-----|
| `apps/openapi/agent/analysis_componet/data_model.py`    | `AnalysisContext` 加 2 个字段 | P0  |
| `apps/openapi/agent/analysis_componet/analysis_tool.py` | 改造 3 个工具                  | P0  |
| `apps/openapi/agent/plan_agent.py`                      | 输出 RPACK                  | P0  |

---

## 四、详细改造方案

### 4.1 改造 1：`AnalysisContext` 增加追踪字段

**文件**: `apps/openapi/agent/analysis_componet/data_model.py`

**问题**: 没有地方记录查询链和最终结果

**改造位置**: `AnalysisContext` 类的 `__init__` 方法

**改造前**:

```python
class AnalysisContext(object):
    def __init__(self,
                 llm_service,
                 message_type,
                 is_chart_output,
                 queue: asyncio.Queue = None, **kwargs):
        self.llm_service = llm_service
        self.message_type = message_type
        self.max_data_size = 1000
        self.insights = []
        self.queue = queue
        self.is_chart_output = is_chart_output
```

**改造后**:

```python
class AnalysisContext(object):
    def __init__(self,
                 llm_service,
                 message_type,
                 is_chart_output,
                 queue: asyncio.Queue = None, **kwargs):
        self.llm_service = llm_service
        self.message_type = message_type
        self.max_data_size = 1000
        self.insights = []
        self.queue = queue
        self.is_chart_output = is_chart_output

        # 【新增】查询链追踪 - 记录所有查询步骤
        self.query_chain = []

        # 【新增】最终结果包 - 分析结束后输出
        self.final_rpack = None
```

---

### 4.2 改造 2：`GetDataTool` 记录查询步骤

**文件**: `apps/openapi/agent/analysis_componet/analysis_tool.py`

**问题**: 取数工具执行了查询，但没有记录到 query_chain

**改造位置**: `GetDataTool._arun()` 方法

#### 第一步：在方法开头记录查询步骤

**改造位置**: `_arun()` 方法开头，`try` 块内第一行

**新增代码**:

```python
async def _arun(self, query: str) -> str:
    try:
        # 【新增】记录查询步骤
        query_id = f"q{len(self.context.query_chain) + 1}"
        self.context.query_chain.append({
            "query_id": query_id,
            "query": query,
            "status": "running",
            "sql": None
        })

        SQLBotLogUtil.info("开始调用智能取数工具")
        # ... 后续代码不变
```

#### 第二步：在取到 SQL 后更新记录

**改造位置**: `elif result_type == "sql_result":` 分支内

**新增代码**:

```python
elif result_type == "sql_result":
sql = result_data["sql"]
enhanced_think_result = result_data["enhanced_think_result"]

# 【新增】更新查询链 - 记录 SQL
if self.context.query_chain:
    self.context.query_chain[-1]["sql"] = sql

if len(enhanced_think_result) != 0:
    await self.context.queue.put(
        self.context.create_result(content=f"\n#### 思考过程\n{enhanced_think_result}\n"))
await self.context.queue.put(
    self.context.create_result(content=f"\n```sql\n{sql.strip()}\n```\n"))
await self.context.queue.put(
    self.context.create_result(content=f"\n#### 3. 执行生成的 SQL \n"))
```

#### 第三步：在取数成功后更新状态

**改造位置**: 方法末尾，`if df is not None:` 分支内

**新增代码**:

```python
if df is not None:
    # 【新增】更新查询链状态为完成
    if self.context.query_chain:
        self.context.query_chain[-1]["status"] = "completed"

    final_result = df.to_json()
    await self.context.queue.put(self.context.create_result(content=f"\n  本次取数结束  \n"))
    return final_result
```

---

### 4.3 改造 3：`SaveInsightTool` 结构化保存证据

**文件**: `apps/openapi/agent/analysis_componet/analysis_tool.py`

**问题**: 保存的洞察没有和查询步骤关联，数据格式也不结构化

**改造位置**: `AnalysisContext.save_insight()` 方法

**改造前**:

```python
def save_insight(self, df: "pd.DataFrame", insight: str, analysis_process: str):
    self.insights.append({"data": df, "insight": insight, "analysis_process": analysis_process})
    return f"保存洞察（{insight}）成功"
```

**改造后**:

```python
def save_insight(self, df: "pd.DataFrame", insight: str, analysis_process: str):
    # 【改造】结构化证据项
    evidence_item = {
        "query_id": self.context.query_chain[-1]["query_id"] if self.context.query_chain else "unknown",
        "insight": insight,
        "analysis_process": analysis_process,
        "data_summary": {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns)
        }
    }

    self.insights.append(evidence_item)

    # 【新增】更新查询链状态
    if self.context.query_chain:
        self.context.query_chain[-1]["insight_saved"] = True

    return f"保存洞察（{insight}）成功"
```

**说明**:

- `data_summary` 只保存元数据，不保存完整 DataFrame（避免结果包过大）
- `query_id` 关联到对应的查询步骤

---

### 4.4 改造 4：`FinalAnswerTool` 构建 RPACK

**文件**: `apps/openapi/agent/analysis_componet/analysis_tool.py`

**问题**: FinalAnswerTool 只返回一句话，没有聚合所有证据

**改造位置**: `FinalAnswerTool` 类

**改造前**（假设）:

```python
class FinalAnswerTool(BaseTool):
    name: str = "final_answer"
    description: str = "最终答案工具"

    def _arun(self, answer: str) -> str:
        return answer
```

**改造后**:

```python
class FinalAnswerTool(BaseTool):
    name: str = "final_answer"
    description: str = "最终答案工具，用于总结分析结论并输出完整证据包"

    class FinalAnswerInput(BaseModel):
        conclusion: str = Field(description="最终结论")

    def _arun(self, conclusion: str) -> str:
        # 【新增】构建 RPACK（Result Package）
        self.context.final_rpack = {
            "conclusion": conclusion,
            "evidence": self.context.insights,
            "query_chain": self.context.query_chain,
            "total_steps": len(self.context.query_chain)
        }

        return f"分析完成。结论：{conclusion}"
```

---

### 4.5 改造 5：`PlanAgent` 输出 RPACK

**文件**: `apps/openapi/agent/plan_agent.py`

**问题**: 分析结束后没有输出结构化的 RPACK

**改造位置**: `execute_plan()` 方法末尾

**改造前**:

```python
await self.queue.put(self.create_result(content=f"\n全部分析结束\n"))
await self.queue.put(self.create_result(message_type="finish"))
return None
```

**改造后**:

```python
# 【新增】输出 RPACK
if self.context.final_rpack:
    import json

    await self.queue.put(self.create_result(
        message_type="rpack",
        content=json.dumps(self.context.final_rpack, ensure_ascii=False, indent=2)
    ))

await self.queue.put(self.create_result(content=f"\n全部分析结束\n"))
await self.queue.put(self.create_result(message_type="finish"))
return None
```

---

## 五、改造后效果

### 5.1 完整数据流

```
用户问题
    ↓
PlanAgent.execute_plan()
    ↓
GetDataTool._arun()
    → 记录 query_chain.append({"query_id": "q1", "query": "...", "sql": "..."})
    ↓
InsightTool._arun()
    → 执行分析算法
    ↓
SaveInsightTool.save_insight()
    → 结构化保存 evidence_item
    → 更新 query_chain[-1]["insight_saved"] = True
    ↓
FinalAnswerTool._arun()
    → 构建 self.context.final_rpack
    ↓
PlanAgent.execute_plan()
    → 输出 JSON 格式 RPACK
```

### 5.2 输出示例

```json
{
  "conclusion": "最近一周高风险登录主要集中在移动端，占总数的 78%",
  "evidence": [
    {
      "query_id": "q1",
      "insight": "OutstandingFirst",
      "analysis_process": "分析最高风险登录的设备类型分布...",
      "data_summary": {
        "row_count": 5,
        "column_count": 2,
        "columns": [
          "device_type",
          "count"
        ]
      }
    }
  ],
  "query_chain": [
    {
      "query_id": "q1",
      "query": "筛选高风险登录，按设备类型分组统计",
      "sql": "SELECT device_type, COUNT(*) as count FROM login_events WHERE risk_score > 80 GROUP BY device_type",
      "status": "completed",
      "insight_saved": true
    }
  ],
  "total_steps": 1
}
```

---

## 六、测试验证

改造完成后，按以下步骤验证：

### 6.1 功能测试

```bash
# 调用深度分析接口
curl -X POST http://localhost:8000/api/openapi/agent/deep-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "question": "分析最近一周的高风险登录",
    "is_chart_output": false
  }'
```

### 6.2 验证清单

- [ ] `query_chain` 正确记录了所有查询步骤
- [ ] 每个查询步骤都有 `query_id`, `query`, `sql`, `status`
- [ ] `evidence` 中的 `query_id` 能关联到 `query_chain`
- [ ] `final_rpack` 包含完整的结论、证据、查询链
- [ ] 流式响应中能收到 `message_type="rpack"` 的消息

---

## 七、常见问题

### Q1: 为什么要用 `query_chain` 而不是直接存数据？

**A**:

- 查询链记录了**分析过程**，不只是结果
- 用户可以看到每一步查了什么、用了什么 SQL
- 便于调试和追溯

### Q2: 为什么 `data_summary` 不存完整数据？

**A**:

- DataFrame 可能很大（几千行）
- RPACK 需要通过网络传输，太大影响性能
- `data_summary` 只存元数据，需要时可以重新查询

### Q3: 如果 Agent 执行失败怎么办？

**A**:

- `query_chain` 中会有 `status: "running"` 的步骤
- 可以根据状态判断哪一步失败了
- 后续可以增加错误处理和重试机制

---

## 八、后续迭代（本期不做）

- [ ] 语义版本管理
- [ ] DAG 可视化
- [ ] 超时控制
- [ ] 置信度评分
- [ ] 数据快照缓存

---

**文档结束**
