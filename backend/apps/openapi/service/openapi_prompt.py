from apps.template.template import get_base_template


def get_myself_template():
    template = get_base_template()
    return template['template']['myself']


def chat_sys_intention():
    return get_myself_template()['chat-intention'].format(lang="简体中文")


def analysis_intention_question(terminologies=""):
    return get_myself_template()['analysis-intention'].format(lang="简体中文", terminologies=terminologies)


def analysis_question(task, intent, role, terminologies=""):
    if role == '' or role is None:
        role = "数据分析师"
    return get_myself_template()['analysis-template'].format(
        lang="简体中文",
        terminologies=terminologies,
        role=role,
        task=task,
        intent=intent
    )
