"""
OpenAPI 数据模型模块

该模块定义了 OpenAPI 接口使用的所有数据模型，包括：
- 请求和响应模型
- 数据验证规则
- 公共头部依赖

作者: huhuhuhr
日期: 2025/01/30
版本: 1.0.0
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict
from typing import List, Union, Optional

from fastapi import Body, Header
from pydantic import BaseModel, validator, Field
from pydantic import field_validator

from apps.chat.models.chat_model import AiModelQuestion
from apps.openapi.service.openapi_prompt import get_myself_template
from apps.template.generate_sql.generator import get_sql_template


class DeepAnalysisRequest(BaseModel):
    """
    深度分析请求模型
    用于单独菜单「深度分析」：Agent 自主规划、多次查数、意图驱动分析
    """
    datasource_id: int = Body(..., description='数据源 ID')
    question: str = Body(..., description='用户分析意图/问题')
    chat_id: Optional[int] = Body(None, description='可选，已有会话 ID；不传则自动创建新会话')
    no_reasoning: Optional[bool] = Body(default=False, description='是否关闭思考过程')
    max_data_length: Optional[int] = Body(default=1000, description='单次取数最大条数')
    is_chart_output: Optional[bool] = Body(default=True, description='是否输出图表')
    max_steps: Optional[int] = Body(default=None, description='最大执行步骤数（迭代次数），不填则自动推断')


class OpenClean(BaseModel):
    """
    聊天记录清理请求模型（仅清理智能问数，不包含深度分析 origin=1）
    支持：按会话 ID 列表、按时间段、清空全部智能问数历史。
    """
    chat_ids: Union[int, List[int]] = Body(
        None,
        description='会话标识或会话标识列表；为空且未指定时间范围时清理当前用户全部智能问数记录'
    )
    start_time: Optional[str] = Body(
        None,
        description='时间段起点（ISO 格式，如 2025-01-01T00:00:00），与 end_time 一起用于按时间段批量清理'
    )
    end_time: Optional[str] = Body(
        None,
        description='时间段终点（ISO 格式），与 start_time 一起用于按时间段批量清理'
    )

    def get_chat_ids(self) -> List[int]:
        """
        获取标准化的chat_id列表
        
        Returns:
            List[int]: 标准化的聊天ID列表
        """
        if isinstance(self.chat_ids, int):
            return [self.chat_ids]
        return self.chat_ids or []


class OpenChat(BaseModel):
    """
    聊天记录查询请求模型
    
    用于根据聊天记录ID查询相关信息
    """
    chat_record_id: int = Body(None, description='会话聊天消息标识')
    chat_id: int = Body(None, description='会话标识')
    db_id: Optional[int] = Body(None, description='数据源标识')
    question: str = Body(None, description='问题内容')
    chat_data_object: Any = Body(None, description='分析问题')
    my_promote: str = Body(None, description='自定义提示词')
    my_schema: Optional[str] = Body(None, description='自定义schema')
    intent: Optional[bool] = Body(default=False, description='是否进行意图检测')
    every: Optional[bool] = Body(default=False, description='逐条分析')
    history_open: Optional[bool] = Body(default=True, description='历史信息打开')
    no_reasoning: Optional[bool] = Body(default=False, description='不思考')

    @field_validator('my_promote', 'my_schema', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """将空字符串转换为 None"""
        if v == '':
            return None
        return v


class OpenChatQuestion(AiModelQuestion):
    """
    开放API聊天问题模型

    继承自AiModelQuestion，扩展了数据源和聊天会话相关字段
    """
    question: str = Body(None, description='用户问题内容')
    chat_id: int = Body(None, description='聊天会话标识')
    db_id: Optional[int] = Body(None, description='数据源标识')
    my_sql: Optional[str] = Body(None, description='自定义sql')
    my_promote: Optional[str] = Body(None, description='自定义提示词')
    my_schema: Optional[str] = Body(None, description='自定义schema')
    intent: Optional[bool] = Body(default=False, description='是否进行意图检测')
    analysis: Optional[bool] = Body(default=False, description='是否分析')
    predict: Optional[bool] = Body(default=False, description='是否预测')
    recommend: Optional[bool] = Body(default=False, description='是否推荐')
    every: Optional[bool] = Body(default=False, description='逐条分析,分析')
    no_reasoning: Optional[bool] = Body(default=True, description='不思考')
    history_open: Optional[bool] = Body(default=True, description='历史信息打开')

    # 原OpenChat中相比于OpenChatQuestion多出的字段
    chat_record_id: int = Body(None, description='会话聊天消息标识')
    chat_data_object: Any = Body(None, description='分析问题')

    # task_type用于选择接口是chat/analysis/predict
    task_type: str = Body("chat", description='用户问题内容')

    # 新增字段用于增强思考
    is_enhanced_think: bool = Body(default=True, description='是否使用增强思考')
    enhanced_think_result: str = Body(default=None, description='增强思考的结果')

    # 新增用户信息
    user_name: str = Body(default=None, description='用户名')

    # 问答时候的模式
    chat_mode: str = Body(default="chat", description='使用什么模式进行问答，plan和chat')

    max_data_length: int = Body(default=1000, description='最大取数长度')

    # 是否输出sqlbot的图表（对于plan模式而言）
    is_chart_output: bool = Body(default=True, description='是否输出sqlbot的图表, 时间会更长')
    analysis_complexity: str = Body(default="medium", description='深度分析复杂度：simple/medium/deep')
    analysis_main_question: Optional[str] = Body(default=None, description='深度分析原始主问题')
    analysis_plan: Optional[Dict[str, Any]] = Body(default=None, description='深度分析显式计划')

    @field_validator('my_promote', 'my_schema', 'my_sql', mode='before')
    @classmethod
    def empty_str_to_none(cls, v):
        """将空字符串转换为 None"""
        if v == '':
            return None
        return v

    # 在原sql生成的prompt里面加入think_result
    def sql_user_question(self, current_time: str, change_title: bool):
        analysis_context = self.sql_analysis_context()
        question_prompt = get_sql_template()['user'].format(engine=self.engine,
                                                            schema=self.db_schema,
                                                            question=self.question,
                                                            rule=self.rule,
                                                            current_time=current_time,
                                                            error_msg=self.error_msg,
                                                            change_title=change_title,
                                                            thinking_result=(self.enhanced_think_result or ''))
        if analysis_context:
            question_prompt += f"\n{analysis_context}"
        return question_prompt

    def sql_analysis_context(self) -> str:
        if not self.analysis_plan:
            return ""

        required_fields = self.analysis_plan.get("required_fields") or []
        forbidden_shapes = self.analysis_plan.get("forbidden_query_shapes") or []
        subquestions = self.analysis_plan.get("subquestions") or []

        required_fields_text = "\n".join(f"- {item}" for item in required_fields) or "- 无"
        forbidden_shapes_text = "\n".join(f"- {item}" for item in forbidden_shapes) or "- 无"
        subquestions_text = "\n".join(f"- {item}" for item in subquestions) or "- 无"

        return (
            "<analysis-execution-context>\n"
            f"<main-question>{self.analysis_main_question or self.question}</main-question>\n"
            f"<task-type>{self.analysis_plan.get('task_type', 'aggregate')}</task-type>\n"
            f"<query-mode>{self.analysis_plan.get('query_mode', 'aggregate')}</query-mode>\n"
            f"<answer-granularity>{self.analysis_plan.get('answer_granularity', 'direct_evidence')}</answer-granularity>\n"
            f"<required-result-shape>{self.analysis_plan.get('required_result_shape', '')}</required-result-shape>\n"
            "<required-fields>\n"
            f"{required_fields_text}\n"
            "</required-fields>\n"
            "<forbidden-query-shapes>\n"
            f"{forbidden_shapes_text}\n"
            "</forbidden-query-shapes>\n"
            "<subquestions>\n"
            f"{subquestions_text}\n"
            "</subquestions>\n"
            "<instruction>\n"
            "先判断当前取数请求属于聚合、排序、对比、趋势还是快照/详情问题，再选择对应的 SQL 形态。"
            "如果 task-type 为 snapshot/detail，则优先返回能直接回答问题的记录级结果，"
            "不要先改写成次数、总量、趋势等聚合问题。"
            "</instruction>\n"
            "</analysis-execution-context>"
        )

    # 获取增强思考的prompt
    def enhanced_think_question(self, current_time: str):
        return get_myself_template()['think_prompt'].format(user_info=self.user_name,
                                                            current_time=current_time,
                                                            schema=self.db_schema,
                                                            query=self.question,
                                                            terminologies=self.terminologies)

    # 获取plan模式的prompt
    def plan_prompt(self, current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')):
        base_prompt = get_myself_template()['plan_prompt'].format(schema=self.db_schema,
                                                                  terminologies=self.terminologies,
                                                                  max_length=self.max_data_length,
                                                                  current_date=current_time)
        complexity = (self.analysis_complexity or "medium").lower()
        plan_json = json.dumps(self.analysis_plan or {}, ensure_ascii=False, indent=2)
        escaped_plan_json = plan_json.replace("{", "{{").replace("}", "}}")
        complexity_rules = {
            "simple": (
                "本次任务复杂度为 simple。优先用最短路径回答问题：通常 1 次取数、最多 2 次取数。"
                "禁止为了凑分析方法而扩展问题；若 1 次取数已足够回答，就直接整理证据并调用 final_answer。"
            ),
            "medium": (
                "本次任务复杂度为 medium。围绕 2～3 个子问题推进，通常 2～4 次取数。"
                "只保留真正能支撑主问题的分析动作，避免重复查同一指标与时间窗。"
            ),
            "deep": (
                "本次任务复杂度为 deep。围绕结构化子问题逐步推进，但依然必须收敛，"
                "每一步都要明确当前正在解决哪个子问题以及该步产出什么证据。"
            ),
        }
        return (
            base_prompt
            + "\n\n## 本次任务执行约束（高优先级）\n"
            + f"- 本次分析不使用历史对话，必须仅基于当前问题独立完成。\n"
            + f"- {complexity_rules.get(complexity, complexity_rules['medium'])}\n"
            + "- 开始执行前，必须先按下方结构化计划理解任务；后续每一步都要围绕计划推进，禁止无关扩展。\n"
            + "- 如果某个子问题已被当前证据充分回答，不要继续为了凑步骤而新增查询。\n"
            + "- 最终报告中的每条核心结论都必须能追溯到已完成的子问题与已获取的数据证据。\n"
            + "\n## 结构化计划（只作为执行约束，不要原样输出给用户）\n"
            + escaped_plan_json
        )


class OpenToken(BaseModel):
    """
    开放API访问令牌响应模型
    
    包含用户认证成功后的访问凭证信息
    """
    access_token: str = Body(..., description='访问令牌，格式为 "bearer {token}"')
    token_type: str = Body(default="bearer", description='令牌类型')
    expire: str = Body(..., description='令牌过期时间')
    chat_id: Optional[int] = Body(default=None, description='聊天会话ID，可选')


class TokenRequest(BaseModel):
    """
    令牌请求模型

    用于通过用户名和密码获取访问令牌的请求体数据模型
    
    Attributes:
        username: 用户名
        password: 密码
        create_chat: 是否在登录时创建聊天会话
    """
    username: str = Body(..., description='用户名')
    password: str = Body(..., description='密码')
    create_chat: bool = Body(default=False, description='是否创建聊天会话')


class DataSourceRequest(BaseModel):
    """
    数据源请求模型

    用于接收获取数据源信息接口的参数
    
    Attributes:
        name: 数据源名称（可选）
        id: 数据源ID（可选）
        
    Note:
        name 和 id 至少需要提供一个，不能同时为空
    """
    name: Optional[str] = Body(default=None, description='数据源名称')
    id: Optional[int] = Body(default=None, description='数据源ID')

    @validator('name', 'id')
    def validate_query_fields(cls, v, values):
        """
        验证查询字段
        
        确保至少有一个查询字段不为空
        
        Args:
            v: 当前字段值
            values: 其他字段值
            
        Raises:
            ValueError: 当所有查询字段都为空时抛出异常
        """
        # 如果当前字段为空，检查其他字段是否也为空
        if v is None:
            other_fields = {k: v for k, v in values.items() if k in ['name', 'id']}
            if all(v is None for v in other_fields.values()):
                raise ValueError("name 和 id 不能同时为空")
        return v

    def validate_query_fields_manual(self) -> 'DataSourceRequest':
        """
        验证查询字段（兼容性方法）
        
        Returns:
            DataSourceRequest: 验证后的请求对象
            
        Raises:
            ValueError: 当查询条件验证失败时抛出异常
        """
        if self.name is None and self.id is None:
            raise ValueError("name 和 id 不能同时为空")
        return self


async def common_headers(
        x_sqlbot_token: Optional[str] = Header(
            None,
            alias="X-Sqlbot-Token",
            description="认证 Token"
        ),
        content_type: Optional[str] = Header(
            None,
            alias="Content-Type",
            description="返回体类型，支持 application/json 和 text/event-stream"
        ),
) -> dict:
    """
    公共请求头依赖函数
    
    用于验证和提取公共请求头信息
    
    Args:
        x_sqlbot_token: SQLBot认证令牌
        content_type: 内容类型
        
    Returns:
        dict: 包含请求头信息的字典
    """
    return {
        "X-Sqlbot-Token": x_sqlbot_token,
        "Content-Type": content_type
    }


@dataclass
class AnalysisIntentPayload:
    role: str
    task: str
    intent: str = ""  # 可选，默认空字符串

    @classmethod
    def from_llm(cls, content: Union[str, Dict[str, Any]]) -> "AnalysisIntentPayload":
        """
        将 LLM 返回的 JSON（或包含 JSON 的字符串）解析为 AnalysisIntentPayload。
        若缺失字段，role/task 会回退为空字符串，intent 默认为空字符串。
        """
        if isinstance(content, str):
            # 提取第一段 {...} 作为 JSON（容错处理：剔除多余文本/Markdown）
            m = re.search(r"\{.*\}", content, flags=re.S)
            if not m:
                raise ValueError("LLM 输出中未找到 JSON 对象")
            data = json.loads(m.group(0))
        else:
            data = content

        return cls(
            role=str(data.get("role", "")).strip(),
            task=str(data.get("task", "")).strip(),
            intent=str(data.get("intent", "")).strip(),
        )

    def to_json(self) -> str:
        """序列化为 JSON 字符串（始终包含三个字段）。"""
        return json.dumps(
            {"role": self.role, "task": self.task, "intent": self.intent},
            ensure_ascii=False
        )


@dataclass
class IntentPayload:
    search: str
    analysis: str
    predict: str = ""  # 可选，默认空字符串

    @classmethod
    def from_llm(cls, content: Union[str, Dict[str, Any]]) -> "IntentPayload":
        """
        将 LLM 返回的 JSON（或包含 JSON 的字符串）解析为 IntentPayload。
        若缺失字段，search/analysis 会回退为空字符串，predict 默认为空字符串。
        """
        if isinstance(content, str):
            # 提取第一段 {...} 作为 JSON（容错处理：剔除多余文本/Markdown）
            m = re.search(r"\{.*\}", content, flags=re.S)
            if not m:
                raise ValueError("LLM 输出中未找到 JSON 对象")
            data = json.loads(m.group(0))
        else:
            data = content

        return cls(
            search=str(data.get("search", "")).strip(),
            analysis=str(data.get("analysis", "")).strip(),
            predict=str(data.get("predict", "")).strip(),
        )

    def to_json(self) -> str:
        """序列化为 JSON 字符串（始终包含三个字段）。"""
        return json.dumps(
            {"search": self.search, "analysis": self.analysis, "predict": self.predict},
            ensure_ascii=False
        )


class DbBindChat(BaseModel):
    title: str = Body(..., description='标题')
    db_id: int = Body(..., description='数据库标记')
    origin: Optional[int] = 0  # 0是页面上，mcp是1，小助手是2


class DatasourceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    type: str
    type_name: str
    configuration: Optional[str]
    create_time: datetime
    create_by: int
    status: str
    num: str
    oid: int
    table_schema: Optional[str] = None
    terminologies: Optional[str] = None



class SinglePgConfig(BaseModel):
    tableName: str = ''
    tableComment: str = ''
    host: str = ''
    port: int = 0
    username: str = ''
    password: str = ''
    database: str = ''
    driver: str = ''
    extraJdbc: str = ''
    dbSchema: str = 'public'
    filename: str = ''
    sheets: List = []
    mode: str = 'service_name'
    timeout: int = 30

    def to_dict(self):
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "database": self.database,
            "driver": self.driver,
            "extraJdbc": self.extraJdbc,
            "dbSchema": self.dbSchema,
            "filename": self.filename,
            "sheets": self.sheets,
            "mode": self.mode,
            "timeout": self.timeout
        }


class DataSourceRequestWithSql(BaseModel):
    db_id: str = Body(..., description='数据源ID')
    sql: str = Body(..., description='SQL查询语句')


from enum import Enum
from typing import Any, Dict


class OutputFormat(str, Enum):
    """输出格式枚举"""
    JSON = "json"
    TABLE = "table"
    CHART = "chart"
    TEXT = "text"
    MARKDOWN = "``"
    EXCEL = "excel"
    CUSTOM = "custom"


class PlanResult(BaseModel):
    """可扩展的计划结果模型"""
    format: OutputFormat = Field(default=OutputFormat.JSON, description="输出格式")
    data: Any = Field(description="实际数据内容")
    metadata: Dict[str, Any] = Field(default={}, description="元数据信息")
    visualization_config: Optional[Dict[str, Any]] = Field(default=None, description="可视化配置")
    custom_properties: Dict[str, Any] = Field(default={}, description="自定义属性")


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
