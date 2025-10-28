# SQLBot OpenAPI Plan接口设计文档（LangChain Agent版）

## 1. 概述

本文档设计一个新的`plan`接口，该接口基于LangChain的Agent架构，具有自主规划和执行能力。接口接收用户问题后，Agent会根据当前状态和LangChain工具自主决定下一步操作，直到完成用户请求。使用LangChain提供的AgentExecutor、create_tool_calling_agent等组件。

## 2. 需求分析

### 2.1 核心功能
- 接收用户输入的问题(question)
- Agent根据当前状态和工具自主规划执行
- 具备自我纠错和动态调整能力
- 实时更新执行状态

### 2.2 Agent执行流程
1. 分析用户问题，确定当前状态和下一步行动
2. 根据状态选择合适的工具执行
3. 观察执行结果，更新内部状态
4. 决定下一步行动，直至任务完成

### 2.3 Agent架构
- Agent：基于LangChain的智能体（使用create_tool_calling_agent）
- Tools：LangChain工具集合（从openapi_llm.py抽取功能）
- AgentExecutor：执行代理任务

## 3. 接口设计

### 3.1 请求模型
基于`openapi.py`中的chat接口设计，创建新的请求模型：

```python
class OpenPlanQuestion(OpenChatQuestion):
    """
    Plan接口问题模型，继承自OpenChatQuestion
    """
    question: str = Body(..., description='用户问题内容')
    chat_id: int = Body(..., description='聊天会话标识')
    db_id: Optional[int] = Body(None, description='数据源标识(可选)')
    max_steps: int = Body(default=10, description='最大执行步骤数')
    enable_retry: bool = Body(default=True, description='是否启用重试机制')
    max_retries: int = Body(default=3, description='最大重试次数')
```

### 3.2 响应模型
```python
class PlanStepStatus(BaseModel):
    """
    执行步骤状态模型
    """
    step: int
    action: str  # 当前采取的行动
    observation: str  # 行动结果/观察
    timestamp: datetime
    details: Optional[dict] = None

class PlanResponse(BaseModel):
    """
    Plan接口响应模型
    """
    plan_id: str
    status: str  # planning, executing, completed, failed
    steps: List[PlanStepStatus]
    result: Optional[dict] = None
    error: Optional[str] = None
```

### 3.3 接口定义
```python
@router.post("/plan", summary="智能规划执行",
             description="基于LangChain Agent架构的智能规划执行接口",
             dependencies=[Depends(common_headers)])
async def plan_execution(
    current_user: CurrentUser,
    plan_question: OpenPlanQuestion,
    current_assistant: CurrentAssistant
) -> StreamingResponse:
    pass
```

## 4. LangChain Agent实现方案

### 4.1 LLMService工具包装类
在`openapi/service`目录下创建`plan_service.py`文件，实现Agent相关类：

```python
from langchain.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Optional, Type
from apps.openapi.service.openapi_llm import LLMService

class LLMServiceWrapper:
    """
    包装openapi_llm.LLMService，提供工具化接口
    """
    def __init__(self, user: CurrentUser, plan_question: OpenPlanQuestion, assistant: CurrentAssistant):
        self.user = user
        self.plan_question = plan_question
        self.assistant = assistant
        self.llm_service = None

    async def initialize_service(self):
        """初始化LLMService"""
        self.llm_service = await LLMService.create(
            self.user,
            self.plan_question,
            self.assistant,
            no_reasoning=self.plan_question.no_reasoning,
            embedding=True
        )

class IdentifyDataSourceTool(BaseTool):
    name = "identify_data_source"
    description = "识别与用户问题相关的数据源"
    
    class InputSchema(BaseModel):
        question: str = Field(description="用户问题")
        user_id: int = Field(description="用户ID")
        
    args_schema: Type[BaseModel] = InputSchema

    def __init__(self, llm_service_wrapper: LLMServiceWrapper):
        super().__init__()
        self.llm_service_wrapper = llm_service_wrapper

    def _run(self, question: str, user_id: int) -> dict:
        """同步运行方法"""
        # 从LLMService或相关模块提取数据源识别逻辑
        from apps.datasource.crud.datasource import get_datasource_list_for_openapi
        from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id
        from apps.openapi.models.openapiModels import DataSourceRequest
        from common.core.db import get_session
        
        with next(get_session()) as session:
            datasources = get_datasource_list_for_openapi(session=session, user=self.llm_service_wrapper.user)
            # 简化逻辑：返回第一个匹配的数据源
            for ds in datasources:
                if any(keyword in question.lower() for keyword in [ds.name.lower(), ds.description.lower() if ds.description else ""]):
                    return {
                        "status": "success",
                        "datasource_id": ds.id,
                        "datasource_name": ds.name,
                        "datasource_description": ds.description
                    }
            
            # 如果没有找到，返回第一个数据源（如果存在）
            if datasources:
                ds = datasources[0]
                return {
                    "status": "success",
                    "datasource_id": ds.id,
                    "datasource_name": ds.name,
                    "datasource_description": ds.description
                }
        
        return {"status": "error", "message": "未找到相关数据源"}

    async def _arun(self, question: str, user_id: int) -> dict:
        """异步运行方法"""
        return self._run(question, user_id)


class GetSchemaInfoTool(BaseTool):
    name = "get_schema_info"
    description = "获取数据源的schema信息"
    
    class InputSchema(BaseModel):
        datasource_id: int = Field(description="数据源ID")
        question: str = Field(description="用户问题")
        
    args_schema: Type[BaseModel] = InputSchema

    def __init__(self, llm_service_wrapper: LLMServiceWrapper):
        super().__init__()
        self.llm_service_wrapper = llm_service_wrapper

    def _run(self, datasource_id: int, question: str) -> dict:
        """同步运行方法"""
        from apps.datasource.crud.datasource import get_table_schema
        from apps.datasource.models.datasource import CoreDatasource
        from common.core.db import get_session
        
        with next(get_session()) as session:
            datasource = session.get(CoreDatasource, datasource_id)
            if not datasource:
                return {"status": "error", "message": "数据源不存在"}
            
            # 获取schema信息
            schema_info = get_table_schema(
                session=session,
                current_user=self.llm_service_wrapper.user,
                ds=datasource,
                question=question
            )
            
            return {
                "status": "success",
                "schema_info": schema_info,
                "table_count": len(schema_info.get('tables', [])) if isinstance(schema_info, dict) else 0
            }

    async def _arun(self, datasource_id: int, question: str) -> dict:
        """异步运行方法"""
        return self._run(datasource_id, question)


class GenerateSQLQueryTool(BaseTool):
    name = "generate_sql_query"
    description = "根据用户问题和schema信息生成SQL查询语句"
    
    class InputSchema(BaseModel):
        question: str = Field(description="用户问题")
        schema_info: str = Field(description="数据源schema信息")
        
    args_schema: Type[BaseModel] = InputSchema

    def __init__(self, llm_service_wrapper: LLMServiceWrapper):
        super().__init__()
        self.llm_service_wrapper = llm_service_wrapper

    def _run(self, question: str, schema_info: str) -> dict:
        """同步运行方法"""
        # 使用LLMService中的能力生成SQL
        # 这里需要访问LLMService中的LLM实例和提示词
        from apps.ai_model.model_factory import get_default_config
        import asyncio
        
        async def async_generate_sql():
            # 初始化LLMService和相关组件
            config = await get_default_config()
            # 这个方法需要获取LLM实例和prompt
            # 模拟使用LLM生成SQL
            return f"SELECT * FROM example_table WHERE description LIKE '%{question}%' LIMIT 100"
        
        # 在当前事件循环中运行异步函数
        try:
            import asyncio
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        sql_query = loop.run_until_complete(async_generate_sql())
        
        return {
            "status": "success",
            "query": sql_query
        }

    async def _arun(self, question: str, schema_info: str) -> dict:
        """异步运行方法"""
        # 使用LLMService中的能力生成SQL
        # 这里需要访问LLMService中的LLM实例和提示词
        # 模拟使用LLM生成SQL
        from apps.ai_model.model_factory import get_default_config
        
        config = await get_default_config()
        # 实际的SQL生成应使用LLM和prompt逻辑
        sql_query = f"SELECT * FROM example_table WHERE description LIKE '%{question}%' LIMIT 100"
        
        return {
            "status": "success",
            "query": sql_query
        }


class ExecuteSQLQueryTool(BaseTool):
    name = "execute_sql_query"
    description = "执行SQL查询语句并返回结果"
    
    class InputSchema(BaseModel):
        datasource_id: int = Field(description="数据源ID")
        sql_query: str = Field(description="SQL查询语句")
        
    args_schema: Type[BaseModel] = InputSchema

    def __init__(self, llm_service_wrapper: LLMServiceWrapper):
        super().__init__()
        self.llm_service_wrapper = llm_service_wrapper

    def _run(self, datasource_id: int, sql_query: str) -> dict:
        """同步运行方法"""
        from apps.datasource.models.datasource import CoreDatasource
        from apps.db.db import exec_sql
        from common.core.db import get_session
        
        with next(get_session()) as session:
            datasource = session.get(CoreDatasource, datasource_id)
            if not datasource:
                return {"status": "error", "message": "数据源不存在"}
            
            # 验证SQL安全性
            from apps.openapi.openapi import _is_safe_sql  # 使用现有的SQL安全检查
            if not _is_safe_sql(sql_query):
                return {"status": "error", "message": "SQL查询不安全"}
            
            # 执行SQL查询
            query_result = exec_sql(ds=datasource, sql=sql_query, origin_column=False)
            
            return {
                "status": "success",
                "rows_count": len(query_result.get('data', [])),
                "columns": query_result.get('fields', []),
                "data_sample": query_result.get('data', [])[:5]  # 只返回前5行作为样本
            }

    async def _arun(self, datasource_id: int, sql_query: str) -> dict:
        """异步运行方法"""
        return self._run(datasource_id, sql_query)


class AnalyzeDataTool(BaseTool):
    name = "analyze_data"
    description = "分析数据查询结果"
    
    class InputSchema(BaseModel):
        question: str = Field(description="用户问题")
        query_result: dict = Field(description="查询结果")
        
    args_schema: Type[BaseModel] = InputSchema

    def __init__(self, llm_service_wrapper: LLMServiceWrapper):
        super().__init__()
        self.llm_service_wrapper = llm_service_wrapper

    def _run(self, question: str, query_result: dict) -> dict:
        """同步运行方法"""
        # 简化实现：返回查询结果的基本分析
        rows_count = len(query_result.get('data', []))
        columns = query_result.get('fields', [])
        
        analysis = f"查询结果包含{rows_count}行数据，{len(columns)}列。"
        if rows_count > 0:
            analysis += f"列包括：{', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}。"
        
        return {
            "status": "success",
            "analysis": analysis,
            "rows_count": rows_count,
            "columns": columns
        }

    async def _arun(self, question: str, query_result: dict) -> dict:
        """异步运行方法"""
        return self._run(question, query_result)


class PlanExecutor:
    def __init__(self, user: CurrentUser, plan_question: OpenPlanQuestion, assistant: CurrentAssistant):
        self.user = user
        self.question = plan_question.question
        self.chat_id = plan_question.chat_id
        self.db_id = plan_question.db_id
        self.max_steps = plan_question.max_steps
        self.enable_retry = plan_question.enable_retry
        self.max_retries = plan_question.max_retries
        self.assistant = assistant
        
        # 初始化LLMService包装器
        self.llm_service_wrapper = LLMServiceWrapper(user, plan_question, assistant)
        
        # 初始化规划跟踪
        self.plan_id = str(uuid.uuid4())
        self.steps_status = []
        self.result = None
        self.error = None

    async def execute_plan(self) -> AsyncGenerator[dict, None]:
        """
        执行规划的主要方法，返回一个异步生成器用于流式响应
        """
        # 初始化LLMService
        await self.llm_service_wrapper.initialize_service()
        
        # 创建LangChain Agent使用的工具
        tools = [
            IdentifyDataSourceTool(self.llm_service_wrapper),
            GetSchemaInfoTool(self.llm_service_wrapper),
            GenerateSQLQueryTool(self.llm_service_wrapper),
            ExecuteSQLQueryTool(self.llm_service_wrapper),
            AnalyzeDataTool(self.llm_service_wrapper)
        ]
        
        # 创建LangChain Agent
        from langchain import hub
        from langchain.agents import create_tool_calling_agent
        from langchain.agents import AgentExecutor
        
        # 获取默认的提示词模板
        prompt = hub.pull("hwchase17/tool-calling-agent")
        
        # 或者使用自定义提示词
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能数据查询助手。请根据用户的问题，按需调用工具完成查询任务。
            
            任务流程：
            1. 首先调用identify_data_source识别数据源
            2. 调用get_schema_info获取schema信息
            3. 使用generate_sql_query生成SQL查询语句
            4. 使用execute_sql_query执行SQL查询
            5. 最后用analyze_data分析查询结果

            严格按照以上顺序调用工具，除非某些步骤可以跳过。"""),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 使用LLMService中的LLM实例
        llm = self.llm_service_wrapper.llm_service.llm
        
        # 创建agent
        agent = create_tool_calling_agent(llm, tools, prompt)
        
        # 创建executor
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=True,
            max_iterations=self.max_steps,
            early_stopping_method="force"
        )
        
        # 执行任务
        step = 0
        try:
            async for chunk in agent_executor.astream({"input": self.question}):
                step += 1
                # 处理agent执行结果
                action = chunk.get('action', 'unknown')
                observation = chunk.get('observation', 'no observation')
                
                self._update_step_status(step, action, observation, chunk)
                
                # 发送状态更新
                yield {
                    "type": "step_status",
                    "step": PlanStepStatus(
                        step=step,
                        action=action,
                        observation=observation,
                        timestamp=datetime.now(),
                        details=chunk
                    )
                }
            
            # 完成后返回最终结果
            yield self._get_final_response()
            
        except Exception as e:
            self.error = str(e)
            error_msg = f"执行计划失败: {str(e)}"
            self._update_step_status(step, "error", error_msg, {"error": str(e)})
            yield self._get_final_response()
    
    def _update_step_status(self, step: int, action: str, observation: str, details: Optional[dict] = None):
        """更新步骤执行状态"""
        step_status = PlanStepStatus(
            step=step,
            action=action,
            observation=observation,
            timestamp=datetime.now(),
            details=details
        )
        self.steps_status.append(step_status)
    
    def _get_final_response(self):
        """获取最终响应"""
        return PlanResponse(
            plan_id=self.plan_id,
            status="completed" if not self.error else "failed",
            steps=self.steps_status,
            result=self.result,
            error=self.error
        )
```

### 4.2 数据模型
在`openapi/models/openapiModels.py`中添加：

```python
class OpenPlanQuestion(OpenChatQuestion):
    """
    Plan接口问题模型
    """
    max_steps: int = Body(default=10, description='最大执行步骤数')
    enable_retry: bool = Body(default=True, description='是否启用重试机制')
    max_retries: int = Body(default=3, description='最大重试次数')
    context: Optional[dict] = Body(default=None, description='执行上下文')

class PlanStepStatus(BaseModel):
    """
    执行步骤状态模型
    """
    step: int
    action: str  # 当前采取的行动
    observation: str  # 行动结果/观察
    timestamp: datetime
    details: Optional[dict] = None

class PlanResponse(BaseModel):
    """
    Plan接口响应模型
    """
    plan_id: str
    status: str  # planning, executing, completed, failed
    steps: List[PlanStepStatus]
    result: Optional[dict] = None
    error: Optional[str] = None
```

### 4.3 接口实现
在`openapi.py`中添加接口：

```python
@router.post("/plan", summary="智能规划执行",
             description="基于LangChain Agent架构的智能规划执行接口",
             dependencies=[Depends(common_headers)])
async def plan_execution(
    current_user: CurrentUser,
    plan_question: OpenPlanQuestion,
    current_assistant: CurrentAssistant
):
    """
    智能规划执行接口
    基于LangChain Agent，根据用户问题自主规划和执行
    """
    try:
        # 创建Plan Agent执行器
        plan_executor = PlanExecutor(
            user=current_user,
            plan_question=plan_question,
            assistant=current_assistant
        )
        
        # 执行规划并返回流式响应
        stream = plan_executor.execute_plan()
        return StreamingResponse(
            merge_plan_streaming_chunks(stream, plan_executor),
            media_type="text/event-stream"
        )
    except Exception as e:
        SQLBotLogUtil.error(f"Plan接口异常: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"规划执行失败: {str(e)}"
        )
```

## 5. LangChain Agent工作原理

### 5.1 Agent决策机制
- 使用LangChain的create_tool_calling_agent创建智能代理
- Agent根据提示词和当前上下文自主决定调用哪个工具
- 使用LLM评估工具调用结果并决定下一步操作

### 5.2 工具系统
- 基于LangChain的BaseTool类创建专业工具
- 每个工具封装特定功能（数据源识别、schema获取、SQL执行等）
- 工具支持同步和异步执行

### 5.3 执行控制
- 使用AgentExecutor管理整个执行流程
- 支持最大迭代次数控制
- 具备早期停止机制

## 6. 错误处理与重试

### 6.1 错误类型
- 数据源访问错误
- SQL生成错误
- 查询执行错误
- 数据分析错误

### 6.2 重试策略
- LangChain Agent内部的重试机制
- 状态回滚机制
- 错误历史记录

## 7. 依赖关系

### 7.1 LangChain依赖
- `langchain.agents`：Agent相关功能
- `langchain.tools`：工具系统
- `langchain_core.prompts`：提示词模板
- `langchain.hub`：获取预定义模板

### 7.2 现有模块依赖
- `apps.db.db.exec_sql`：执行SQL查询
- `apps.openapi.service.openapi_llm.LLMService`：AI处理能力
- `apps.openapi.dao.openapiDao`：数据访问操作
- `common.utils.utils.SQLBotLogUtil`：日志记录
- 复用`apps.openapi.openapi._is_safe_sql`：SQL安全检查

### 7.3 新增模块
- `apps.openapi.service.plan_service`：Agent执行逻辑
- 扩展`apps.openapi.models.openapiModels`：新增数据模型

## 8. 安全考虑

- 用户权限验证（数据源访问权限）
- SQL注入防护（复用现有的SQL安全检查）
- 输入参数验证
- 会话管理
- LLM调用的安全性

## 9. 结果输出的灵活扩展设计

### 9.1 可扩展的输出格式
为了实现灵活的输出，我们设计了支持多种输出格式的架构：

```python
class OutputFormat(str, Enum):
    """输出格式枚举"""
    JSON = "json"
    TABLE = "table"
    CHART = "chart"
    TEXT = "text"
    MARKDOWN = "markdown"
    EXCEL = "excel"
    CUSTOM = "custom"

class PlanResult(BaseModel):
    """可扩展的计划结果模型"""
    format: OutputFormat = Field(default=OutputFormat.JSON, description="输出格式")
    data: Any = Field(description="实际数据内容")
    metadata: Dict[str, Any] = Field(default={}, description="元数据信息")
    visualization_config: Optional[Dict[str, Any]] = Field(default=None, description="可视化配置")
    custom_properties: Dict[str, Any] = Field(default={}, description="自定义属性")
    
    def to_json(self) -> str:
        """转换为JSON格式"""
        return self.json()
    
    def to_table(self) -> str:
        """转换为表格格式"""
        # 使用pandas或其他库实现表格转换
        import pandas as pd
        if isinstance(self.data, list) and len(self.data) > 0:
            df = pd.DataFrame(self.data)
            return df.to_string()
        return str(self.data)
    
    def to_chart(self, chart_type: str = "bar") -> Dict[str, Any]:
        """转换为图表格式"""
        # 实现图表配置生成逻辑
        return {
            "chart_type": chart_type,
            "data": self.data,
            "config": self.visualization_config or {}
        }
    
    def to_custom_format(self, formatter_func: callable) -> Any:
        """通过自定义函数转换格式"""
        return formatter_func(self.data, self.metadata)
```

### 9.2 输出处理器系统
```python
class OutputProcessor:
    """输出处理器基类"""
    def __init__(self):
        self.processors = {}
    
    def register_processor(self, format_type: str, processor_func: callable):
        """注册新的输出处理器"""
        self.processors[format_type] = processor_func
    
    def process(self, result: PlanResult) -> Any:
        """处理输出结果"""
        if result.format in self.processors:
            return self.processors[result.format](result)
        else:
            # 默认处理器
            return result.data

class JSONOutputProcessor(OutputProcessor):
    """JSON输出处理器"""
    def process(self, result: PlanResult) -> str:
        return result.to_json()

class TableOutputProcessor(OutputProcessor):
    """表格输出处理器"""
    def process(self, result: PlanResult) -> str:
        return result.to_table()

class ChartOutputProcessor(OutputProcessor):
    """图表输出处理器"""
    def process(self, result: PlanResult) -> Dict[str, Any]:
        chart_type = result.metadata.get("chart_type", "bar")
        return result.to_chart(chart_type)
```

### 9.3 插件式结果处理
```python
class ResultHandlerRegistry:
    """结果处理器注册表"""
    def __init__(self):
        self.handlers = {}
    
    def register_handler(self, handler_name: str, handler_class):
        """注册结果处理器"""
        self.handlers[handler_name] = handler_class
    
    def get_handler(self, handler_name: str):
        """获取结果处理器"""
        if handler_name in self.handlers:
            return self.handlers[handler_name]()
        else:
            # 返回默认处理器
            return DefaultResultHandler()

class BaseResultHandler:
    """结果处理器基类"""
    def handle(self, data: Any, format_type: str, options: Dict[str, Any] = None) -> Any:
        """处理结果数据"""
        raise NotImplementedError

class DefaultResultHandler(BaseResultHandler):
    """默认结果处理器"""
    def handle(self, data: Any, format_type: str, options: Dict[str, Any] = None) -> Any:
        if format_type == "json":
            return json.dumps(data, ensure_ascii=False)
        elif format_type == "table":
            import pandas as pd
            return pd.DataFrame(data).to_html()
        # 其他格式处理
        return data
```

### 9.4 扩展示例
```python
# 示例：扩展一个新的输出格式
class PDFOutputProcessor(OutputProcessor):
    """PDF输出处理器 - 示例扩展"""
    def process(self, result: PlanResult) -> bytes:
        # 实现PDF生成逻辑
        # 可以使用reportlab等库
        pass

# 注册新的处理器
output_processor = OutputProcessor()
output_processor.register_processor("pdf", PDFOutputProcessor)

# 或者扩展结果处理器
result_handler_registry = ResultHandlerRegistry()
result_handler_registry.register_handler("pdf_report", PDFOutputProcessor)
```

## 10. 测试计划

- 单元测试：各个工具的独立测试
- 集成测试：Agent决策流程测试
- 错误处理测试：验证错误处理和重试机制
- 安全测试：验证权限控制和输入验证
- LangChain Agent功能测试
- 输出格式扩展测试：验证不同输出格式的正确性
- 自定义输出处理器测试：验证扩展机制的有效性