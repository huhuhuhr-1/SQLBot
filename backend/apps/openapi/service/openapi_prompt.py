from apps.template.template import get_base_template
from pathlib import Path
from functools import cache


def get_myself_template():
    template = get_base_template()
    return template['template']['myself']


@cache
def _load_semantic_expansion_template():
    """加载语义扩展模板"""
    semantic_template_path = Path(__file__).parent.parent.parent / 'templates' / 'semantic_expansion.yaml'
    try:
        with open(semantic_template_path, 'r', encoding='utf-8') as f:
            import yaml
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Semantic expansion template file not found at {semantic_template_path}")


def get_semantic_expansion_template():
    """获取语义扩展模板"""
    template = _load_semantic_expansion_template()
    return template['template']['semantic-expansion']


def chat_sys_intention():
    return get_myself_template()['chat-intention'].format(lang="简体中文")


def analysis_intention_question(terminologies=""):
    return get_myself_template()['analysis-intention'].format(lang="简体中文", terminologies=terminologies)


def analysis_question(task, intent, role, terminologies=""):
    """
    根据任务、意图和角色生成分析问题的提示词

    Args:
        task: 具体任务描述
        intent: 意图类型
        role: 角色定义
        terminologies: 术语列表

    Returns:
        格式化后的提示词模板
    """
    # 角色默认值处理
    if not role:
        role = "数据分析师"

    # 获取基础模板
    template = get_myself_template()

    # 优先使用特定意图的模板，否则使用默认分析模板
    intent_template = template.get(intent)
    if intent_template is None:
        intent_template = template.get('analysis-template')

    # 格式化模板
    return intent_template.format(
        lang="简体中文",
        terminologies=terminologies,
        role=role,
        task=task,
        intent=intent
    )
