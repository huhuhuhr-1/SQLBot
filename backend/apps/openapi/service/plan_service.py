from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
import uuid
from langchain.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
from typing import Type, Union

from apps.openapi.service.openapi_llm import LLMService
from apps.datasource.crud.datasource import get_datasource_list_for_openapi, get_table_schema
from apps.datasource.models.datasource import CoreDatasource
from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id
from apps.openapi.models.openapiModels import DataSourceRequest, OutputFormat, PlanResult, PlanStepStatus, PlanResponse
from apps.db.db import exec_sql
from common.core.db import get_session
from common.core.deps import CurrentUser, CurrentAssistant
from common.utils.utils import SQLBotLogUtil
from apps.openapi.openapi import _is_safe_sql  # 复用现有的SQL安全检查


class LLMServiceWrapper:
    """
    包装openapi_llm.LLMService，提供工具化接口
    """
    def __init__(self, user: CurrentUser, plan_question: 'OpenPlanQuestion', assistant: CurrentAssistant):
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
        from apps.datasource.crud.datasource import get_datasource_list_for_openapi
        from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id
        from apps.openapi.models.openapiModels import DataSourceRequest
        from common.core.db import get_session
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            datasources = get_datasource_list_for_openapi(session=session, user=self.llm_service_wrapper.user)
            # 根据问题关键词匹配数据源
            for ds in datasources:
                if any(keyword in question.lower() for keyword in [ds.name.lower(), ds.description.lower() if ds.description else ""]):
                    return {
                        "status": "success",
                        "datasource_id": ds.id,
                        "datasource_name": ds.name,
                        "datasource_description": ds.description
                    }
            
            # 如果没有找到匹配的数据源，返回第一个数据源（如果存在）
            if datasources:
                ds = datasources[0]
                return {
                    "status": "success",
                    "datasource_id": ds.id,
                    "datasource_name": ds.name,
                    "datasource_description": ds.description
                }
            
            return {"status": "error", "message": "未找到相关数据源"}
        finally:
            session.close()

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
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            datasource = session.get(CoreDatasource, datasource_id)
            if not datasource:
                return {"status": "error", "message": "数据源不存在"}
            
            # 获取schema信息
            schema_info = get_table_schema(
                session=session,
                current_user=self.llm_service_wrapper.user,
                ds=datasource,
                question=question,
                embedding=False
            )
            
            return {
                "status": "success",
                "schema_info": schema_info,
                "table_count": len(schema_info.get('tables', [])) if isinstance(schema_info, dict) else 0
            }
        finally:
            session.close()

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
        # 为了实现完整的SQL生成，我们需要使用LLM来分析问题和schema
        # 这部分需要使用LLMService内部的逻辑
        # 作为示例，我们构造一个基本的SQL查询
        
        # 从问题中提取关键词
        keywords = question.lower()
        if "count" in keywords or "数量" in keywords:
            sql_query = f"SELECT COUNT(*) FROM example_table WHERE description LIKE '%{question}%'"
        elif "top" in keywords or "top" in keywords:
            sql_query = f"SELECT * FROM example_table WHERE description LIKE '%{question}%' LIMIT 10"
        else:
            sql_query = f"SELECT * FROM example_table WHERE description LIKE '%{question}%' LIMIT 100"
        
        return {
            "status": "success",
            "query": sql_query
        }

    async def _arun(self, question: str, schema_info: str) -> dict:
        """异步运行方法"""
        # 在实际实现中，我们会调用LLMService中的SQL生成逻辑
        # 但现在我们使用简化版本
        keywords = question.lower()
        if "count" in keywords or "数量" in keywords:
            sql_query = f"SELECT COUNT(*) FROM example_table WHERE description LIKE '%{question}%'"
        elif "top" in keywords or "top" in keywords:
            sql_query = f"SELECT * FROM example_table WHERE description LIKE '%{question}%' LIMIT 10"
        else:
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
        
        session_gen = get_session()
        session = next(session_gen)
        try:
            datasource = session.get(CoreDatasource, datasource_id)
            if not datasource:
                return {"status": "error", "message": "数据源不存在"}
            
            # 验证SQL安全性
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
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
        finally:
            session.close()

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
        
        analysis = f"根据您的问题'{question}'，查询结果包含{rows_count}行数据，{len(columns)}列。"
        if rows_count > 0:
            analysis += f"列包括：{', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}。"
            # 添加前几行数据的摘要
            analysis += "前几行数据摘要："
            for i, row in enumerate(query_result.get('data', [])[:3]):
                analysis += f"第{i+1}行: "
                for key, value in list(row.items())[:3]:  # 显示前3个字段
                    analysis += f"{key}={value}, "
                analysis = analysis.rstrip(', ') + "; "
        
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
    def __init__(self, user: CurrentUser, plan_question: 'OpenPlanQuestion', assistant: CurrentAssistant):
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
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
        from apps.ai_model.model_factory import get_default_config
        
        # 获取默认的提示词模板
        try:
            # 尝试从hub获取，如果失败则使用自定义模板
            prompt = hub.pull("hwchase17/tool-calling-agent")
        except Exception:
            # 使用自定义提示词
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
            # 这里我们不能直接使用astream，因为我们需要格式化输出
            # 我们使用invoke方法获取完整结果
            result = agent_executor.invoke({
                "input": self.question
            })
            
            # 处理结果
            final_analysis = result.get('output', '分析完成')
            
            # 添加最终步骤状态
            step_status = PlanStepStatus(
                step=1,
                action="final_analysis",
                observation=final_analysis,
                timestamp=datetime.now(),
                details=result
            )
            self.steps_status.append(step_status)
            
            # 生成最终响应
            final_response = PlanResponse(
                plan_id=self.plan_id,
                status="completed",
                steps=self.steps_status,
                result={
                    "analysis": final_analysis,
                    "data": result  # 包含完整的agent执行结果
                }
            )
            
            yield final_response
            
        except Exception as e:
            self.error = str(e)
            error_msg = f"执行计划失败: {str(e)}"
            step_status = PlanStepStatus(
                step=1,
                action="error",
                observation=error_msg,
                timestamp=datetime.now(),
                details={"error": str(e)}
            )
            self.steps_status.append(step_status)
            
            final_response = PlanResponse(
                plan_id=self.plan_id,
                status="failed",
                steps=self.steps_status,
                result=None,
                error=str(e)
            )
            yield final_response


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
        return result.json()


class TableOutputProcessor(OutputProcessor):
    """表格输出处理器"""
    def process(self, result: PlanResult) -> str:
        import pandas as pd
        if isinstance(result.data, list) and len(result.data) > 0:
            df = pd.DataFrame(result.data)
            return df.to_string()
        return str(result.data)


class ChartOutputProcessor(OutputProcessor):
    """图表输出处理器"""
    def process(self, result: PlanResult) -> Dict[str, Any]:
        chart_type = result.metadata.get("chart_type", "bar")
        return result.to_chart(chart_type) if hasattr(result, 'to_chart') else {
            "chart_type": chart_type,
            "data": result.data,
            "config": result.visualization_config or {}
        }


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
            import json
            return json.dumps(data, ensure_ascii=False, default=str)
        elif format_type == "table":
            import pandas as pd
            if isinstance(data, dict) and 'data' in data:
                return pd.DataFrame(data['data']).to_html()
            elif isinstance(data, list):
                return pd.DataFrame(data).to_html()
            else:
                return str(data)
        # 其他格式处理
        return data