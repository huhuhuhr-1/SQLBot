"""
默认提示词与 LLM 优化接口：供设置-自定义提示词页获取默认模板、变量说明及优化提示词。
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from apps.template.generate_sql.generator import get_sql_template
from apps.template.generate_analysis.generator import get_analysis_template
from apps.template.generate_predict.generator import get_predict_template

router = APIRouter(tags=["System"], prefix="/system", include_in_schema=False)

# 三类与 chat_model 中 .format 占位符一致
DEFAULT_VARIABLES = {
    "GENERATE_SQL": [
        {"name": "engine", "description": "数据库引擎及版本"},
        {"name": "schema", "description": "M-Schema 表结构"},
        {"name": "question", "description": "用户问题"},
        {"name": "lang", "description": "回答语言"},
        {"name": "terminologies", "description": "术语表"},
        {"name": "data_training", "description": "数据训练/示例"},
        {"name": "custom_prompt", "description": "自定义提示词（本处注入）"},
        {"name": "process_check", "description": "SQL 生成检查步骤"},
        {"name": "base_sql_rules", "description": "SQL 规则"},
        {"name": "basic_sql_examples", "description": "SQL 示例"},
        {"name": "example_engine", "description": "示例引擎"},
        {"name": "example_answer_1", "description": "示例答案 1"},
        {"name": "example_answer_2", "description": "示例答案 2"},
        {"name": "example_answer_3", "description": "示例答案 3"},
    ],
    "ANALYSIS": [
        {"name": "lang", "description": "回答语言"},
        {"name": "terminologies", "description": "术语表"},
        {"name": "custom_prompt", "description": "自定义提示词（本处注入）"},
    ],
    "PREDICT_DATA": [
        {"name": "lang", "description": "回答语言"},
        {"name": "custom_prompt", "description": "自定义提示词（本处注入）"},
    ],
}


@router.get("/default-prompts", summary="获取三类默认提示词内容与可用变量")
async def get_default_prompts():
    """
    返回智能问数(GENERATE_SQL)、数据分析(ANALYSIS)、数据预测(PREDICT_DATA) 的默认 system 模板内容及变量列表。
    便于自定义提示词与默认提示词无缝切换时参考变量。
    """
    sql_tpl = get_sql_template()
    analysis_tpl = get_analysis_template()
    predict_tpl = get_predict_template()
    return {
        "GENERATE_SQL": {
            "defaultContent": sql_tpl.get("system", ""),
            "variables": DEFAULT_VARIABLES["GENERATE_SQL"],
        },
        "ANALYSIS": {
            "defaultContent": analysis_tpl.get("system", ""),
            "variables": DEFAULT_VARIABLES["ANALYSIS"],
        },
        "PREDICT_DATA": {
            "defaultContent": predict_tpl.get("system", ""),
            "variables": DEFAULT_VARIABLES["PREDICT_DATA"],
        },
    }


class PromptOptimizeRequest(BaseModel):
    type: str = Field(..., description="GENERATE_SQL | ANALYSIS | PREDICT_DATA")
    prompt: str = Field(..., description="用户输入的提示词内容")


class PromptOptimizeResponse(BaseModel):
    optimized: str = Field(..., description="优化后的提示词")


@router.post("/prompt/optimize", response_model=PromptOptimizeResponse, summary="使用 LLM 优化提示词")
async def optimize_prompt(body: PromptOptimizeRequest):
    """
    使用当前可用 LLM 对用户输入的提示词进行美化/优化，保持与默认提示词变量兼容。
    返回优化后的纯文本提示词。
    """
    try:
        from apps.openapi.llm.my_llm import LLMManager
        from langchain_core.messages import SystemMessage, HumanMessage
    except Exception:
        return PromptOptimizeResponse(optimized=body.prompt)
    try:
        llm = await LLMManager.get_default_llm()
    except Exception:
        return PromptOptimizeResponse(optimized=body.prompt)
    if llm is None:
        return PromptOptimizeResponse(optimized=body.prompt)
    system = (
        "你是一个提示词优化助手。用户会给你一段用于「智能问数 / 数据分析 / 数据预测」场景的提示词。"
        "请在不改变用户意图的前提下，对提示词进行润色、结构化（如分点、加标题），使其更清晰、易读。"
        "若提示词中涉及可替换变量（如 {lang}、{custom_prompt} 等），请保留这些占位符不变。"
        "只输出优化后的提示词正文，不要输出解释。"
    )
    user_msg = f"请优化以下提示词：\n\n{body.prompt}"
    try:
        messages = [SystemMessage(content=system), HumanMessage(content=user_msg)]
        result = llm.invoke(messages)
        content = result.content if hasattr(result, "content") else str(result)
        return PromptOptimizeResponse(optimized=(content or body.prompt).strip())
    except Exception:
        return PromptOptimizeResponse(optimized=body.prompt)
