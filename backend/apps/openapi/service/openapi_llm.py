import concurrent
import json
import os
import traceback
import urllib.parse
import warnings
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime
# modify huhuhuhr
from string import Template
from typing import Any, List, Optional, Union, Dict, Iterator

import orjson
import pandas as pd
import requests
import sqlparse
# modify by huhuhuhr
from sqlalchemy.exc import PendingRollbackError
import tiktoken
from langchain.chat_models.base import BaseChatModel
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, BaseMessageChunk
from sqlalchemy import and_, select
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlbot_xpack.custom_prompt.curd.custom_prompt import find_custom_prompts
from sqlbot_xpack.custom_prompt.models.custom_prompt_model import CustomPromptTypeEnum
from sqlbot_xpack.license.license_manage import SQLBotLicenseUtil
from sqlmodel import Session

from apps.ai_model.model_factory import LLMConfig, LLMFactory, get_default_config
from apps.chat.curd.chat import save_question, save_sql_answer, save_sql, \
    save_error_message, save_sql_exec_data, save_chart_answer, save_chart, \
    finish_record, save_analysis_answer, save_predict_answer, save_predict_data, \
    save_select_datasource_answer, save_recommend_question_answer, \
    get_old_questions, save_analysis_predict_record, rename_chat, get_chart_config, \
    get_chat_chart_data, list_generate_sql_logs, list_generate_chart_logs, start_log, end_log, \
    get_last_execute_sql_error, format_json_data, format_chart_fields
from apps.chat.models.chat_model import ChatQuestion, ChatRecord, Chat, RenameChat, ChatLog, OperationEnum, \
    ChatFinishStep, AxisObj
from apps.data_training.curd.data_training import get_training_template
from apps.datasource.crud.datasource import get_table_schema
from apps.datasource.crud.permission import get_row_permission_filters, is_normal_user
from apps.datasource.embedding.ds_embedding import get_ds_embedding
from apps.datasource.models.datasource import CoreDatasource
from apps.db.db import exec_sql, get_version, check_connection
# modify by huhuhuhr
from apps.openapi.dao.openapiDao import select_one, get_datasource_by_name_or_id
from apps.openapi.models.openapiModels import AnalysisIntentPayload, DataSourceRequest
from apps.openapi.models.openapiModels import OpenChatQuestion
from apps.openapi.service.openapi_prompt import analysis_question
from apps.system.crud.assistant import AssistantOutDs, AssistantOutDsFactory, get_assistant_ds
from apps.system.schemas.system_schema import AssistantOutDsSchema
from apps.terminology.curd.terminology import get_terminology_template
from common.core.config import settings
# modify by huuhuhuhr
from common.core.db import engine, get_session
from common.core.deps import CurrentAssistant, CurrentUser
from common.error import SingleMessageError, SQLBotDBError, ParseSQLResultError, SQLBotDBConnectionError
from common.utils.data_format import DataFormat
from common.utils.utils import SQLBotLogUtil, extract_nested_json, prepare_for_orjson

warnings.filterwarnings("ignore")

base_message_count_limit = 6

executor = ThreadPoolExecutor(max_workers=200)

dynamic_ds_types = [1, 3]
dynamic_subsql_prefix = 'select * from sqlbot_dynamic_temp_table_'

session_maker = scoped_session(sessionmaker(bind=engine, class_=Session))


class LLMService:
    ds: CoreDatasource
    # modify by huhuhuhr
    chat_question: OpenChatQuestion
    record: ChatRecord
    config: LLMConfig
    llm: BaseChatModel
    sql_message: List[Union[BaseMessage, dict[str, Any]]] = []
    chart_message: List[Union[BaseMessage, dict[str, Any]]] = []

    # session: Session = db_session
    current_user: CurrentUser
    current_assistant: Optional[CurrentAssistant] = None
    out_ds_instance: Optional[AssistantOutDs] = None
    change_title: bool = False

    generate_sql_logs: List[ChatLog] = []
    generate_chart_logs: List[ChatLog] = []

    current_logs: dict[OperationEnum, ChatLog] = {}

    chunk_list: List[str] = []
    future: Future

    last_execute_sql_error: str = None

    # modify by huhuhuhr 20250925 新增embedding
    def __init__(self, session: Session, current_user: CurrentUser,
                 chat_question: OpenChatQuestion,
                 current_assistant: Optional[CurrentAssistant] = None, no_reasoning: bool = False,
                 embedding: bool = False, config: LLMConfig = None):
        # ✅ 确保是字符串，并设置环境变量 modify huhuhuhr
        os.environ["TIKTOKEN_CACHE_DIR"] = str(settings.TIKTOKEN_CACHE_DIR)
        self._encoder = tiktoken.get_encoding("o200k_base")
        self.chunk_list = []
        self.current_user = current_user
        self.current_assistant = current_assistant
        chat_id = chat_question.chat_id
        chat: Chat | None = session.get(Chat, chat_id)
        if not chat:
            raise SingleMessageError(f"Chat with id {chat_id} not found")
        ds: CoreDatasource | AssistantOutDsSchema | None = None
        if chat.datasource:
            # Get available datasource
            if current_assistant and current_assistant.type in dynamic_ds_types:
                self.out_ds_instance = AssistantOutDsFactory.get_instance(current_assistant)
                ds = self.out_ds_instance.get_ds(chat.datasource)
                if not ds:
                    raise SingleMessageError("No available datasource configuration found")
                chat_question.engine = ds.type + get_version(ds)
                chat_question.db_schema = self.out_ds_instance.get_db_schema(ds.id, chat_question.question)
            else:
                ds = session.get(CoreDatasource, chat.datasource)
                if not ds:
                    raise SingleMessageError("No available datasource configuration found")
                chat_question.engine = (ds.type_name if ds.type != 'excel' else 'PostgreSQL') + get_version(ds)
                chat_question.db_schema = get_table_schema(session=session, current_user=current_user, ds=ds,
                                                           question=chat_question.question, embedding=embedding)

        self.generate_sql_logs = list_generate_sql_logs(session=session, chart_id=chat_id)
        self.generate_chart_logs = list_generate_chart_logs(session=session, chart_id=chat_id)

        self.change_title = len(self.generate_sql_logs) == 0

        chat_question.lang = get_lang_name(current_user.language)

        self.ds = (
            ds if isinstance(ds, AssistantOutDsSchema) else CoreDatasource(**ds.model_dump())) if ds else None
        self.chat_question = chat_question
        self.config = config
        if no_reasoning:
            # only work while using qwen
            if self.config.additional_params:
                if self.config.additional_params.get('extra_body'):
                    if self.config.additional_params.get('extra_body').get('enable_thinking'):
                        del self.config.additional_params['extra_body']['enable_thinking']

        #  modify by huhuhuhr 20250923
        if chat_question.no_reasoning is True:
            SQLBotLogUtil.info("qwen no reasoning")
            # 确保 additional_params 存在
            if self.config.additional_params:
                extra_body = self.config.additional_params.setdefault('extra_body', {})
                # 设置 chat_template_kwargs，确保不会覆盖已有配置
                chat_template_kwargs = extra_body.setdefault('chat_template_kwargs', {})
                chat_template_kwargs['enable_thinking'] = False

        self.chat_question.ai_modal_id = self.config.model_id
        self.chat_question.ai_modal_name = self.config.model_name

        # Create LLM instance through factory
        llm_instance = LLMFactory.create_llm(self.config)
        self.llm = llm_instance.llm

        # get last_execute_sql_error
        last_execute_sql_error = get_last_execute_sql_error(session, self.chat_question.chat_id)
        if last_execute_sql_error:
            self.chat_question.error_msg = f'''<error-msg>
{last_execute_sql_error}
</error-msg>'''
        else:
            self.chat_question.error_msg = ''

    @classmethod
    async def create(cls, *args, **kwargs):
        config: LLMConfig = await get_default_config()
        instance = cls(*args, **kwargs, config=config)
        return instance

    def is_running(self, timeout=0.5):
        try:
            r = concurrent.futures.wait([self.future], timeout)
            if len(r.not_done) > 0:
                return True
            else:
                return False
        except Exception as e:
            return True

    # modify by huhuhuhr
    def init_messages(self, _session: Session):
        # modify by huhuhuhr chat的history开关
        if self.chat_question.history_open is False:
            last_sql_messages = []
        else:
            last_sql_messages: List[dict[str, Any]] = self.generate_sql_logs[-1].messages if len(
                self.generate_sql_logs) > 0 else []
        # todo maybe can configure
        count_limit = 0 - base_message_count_limit

        self.sql_message = []
        # modify by huhuhuhr 自定义提示词
        if self.chat_question.my_promote is not None and self.chat_question.my_promote.strip() != '':
            self.sql_message.append(SystemMessage(
                content=self.chat_question.sql_sys_question(self.ds.type, settings.GENERATE_SQL_QUERY_LIMIT_ENABLED)))
            sys_promote = self.get_my_sys_prompt(payload=None, _session=_session)
            self.sql_message.append(SystemMessage(content=sys_promote))
        else:
            if self.chat_question.my_schema is not None:
                self.sql_message.append(SystemMessage(
                    content=self.chat_question.sql_sys_question_with_schema(self.chat_question.my_schema)))
            else:
                self.sql_message.append(SystemMessage(content=self.chat_question.sql_sys_question(self.ds.type,
                                                                                                  settings.GENERATE_SQL_QUERY_LIMIT_ENABLED)))
        if last_sql_messages is not None and len(last_sql_messages) > 0:
            # limit count
            for last_sql_message in last_sql_messages[count_limit:]:
                _msg: BaseMessage
                if last_sql_message['type'] == 'human':
                    _msg = HumanMessage(content=last_sql_message['content'])
                    self.sql_message.append(_msg)
                elif last_sql_message['type'] == 'ai':
                    _msg = AIMessage(content=last_sql_message['content'])
                    self.sql_message.append(_msg)

        last_chart_messages: List[dict[str, Any]] = self.generate_chart_logs[-1].messages if len(
            self.generate_chart_logs) > 0 else []

        self.chart_message = []
        # add sys prompt
        self.chart_message.append(SystemMessage(content=self.chat_question.chart_sys_question()))

        if last_chart_messages is not None and len(last_chart_messages) > 0:
            # limit count
            for last_chart_message in last_chart_messages:
                _msg: BaseMessage
                if last_chart_message.get('type') == 'human':
                    _msg = HumanMessage(content=last_chart_message.get('content'))
                    self.chart_message.append(_msg)
                elif last_chart_message.get('type') == 'ai':
                    _msg = AIMessage(content=last_chart_message.get('content'))
                    self.chart_message.append(_msg)

    def init_record(self, session: Session) -> ChatRecord:
        self.record = save_question(session=session, current_user=self.current_user, question=self.chat_question)
        return self.record

    def get_record(self):
        return self.record

    def set_record(self, record: ChatRecord):
        self.record = record

    def get_fields_from_chart(self, _session: Session):
        chart_info = get_chart_config(_session, self.record.id)
        return format_chart_fields(chart_info)

    # modify by huhuhuhr
    def generate_analysis(self, _session: Session,
                          dataStr: str = None, payload: AnalysisIntentPayload = None):
        fields = self.get_fields_from_chart()
        self.chat_question.fields = orjson.dumps(fields).decode()
        # modify by huhuhuhr 只分析数据的时候由于没有上级的recordId,所以不会有chat无法提取fields
        if self.chat_question.fields is None or self.chat_question.fields == '[]':
            self.record.ai_modal_id = self.chat_question.ai_modal_id
            self.record.create_by = self.current_user.oid
            try:
                for session in get_session():
                    datasource: CoreDatasource = get_datasource_by_name_or_id(
                        session=session,
                        user=self.current_user,
                        query=DataSourceRequest(id=self.chat_question.db_id)
                    )
                    self.chat_question.fields = get_table_schema(session=_session,
                                                                 current_user=self.current_user,
                                                                 ds=datasource,
                                                                 question=self.chat_question.question)
            except Exception as e:
                SQLBotLogUtil.error(f"get table failed: {e}")
        # 按照字符数量阈值处理数据，而不是按行数
        if dataStr is not None:
            raw_data = json.loads(dataStr)
        else:
            data = get_chat_chart_data(_session, self.record.id)
            raw_data = data.get('data')
        max_token_chars = settings.MAX_TOKEN_CHUNK  # 设置字符阈值，可根据需要调整
        self.chat_question.data = orjson.dumps(raw_data).decode()
        analysis_msg: List[Union[BaseMessage, dict[str, Any]]] = []

        ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None
        self.chat_question.terminologies = get_terminology_template(_session, self.chat_question.question,
                                                                    self.current_user.oid, ds_id)
        if SQLBotLicenseUtil.valid():
            self.chat_question.custom_prompt = find_custom_prompts(_session, CustomPromptTypeEnum.ANALYSIS,
                                                                   self.current_user.oid, ds_id)
        # 系统提示词 modify by huhuhuhr
        sys_prompt = self.get_analysis_sys_prompt(payload)
        analysis_msg.append(SystemMessage(content=sys_prompt))
        if raw_data:
            # 将数据转换为JSON字符串以估算字符数
            data_str = orjson.dumps(raw_data).decode()
            # 计算数据量
            total_prompt_tokens = self.count_tokens(data_str)

            SQLBotLogUtil.info(f'Estimated total prompt tokens: {total_prompt_tokens}')

            if (self.chat_question.every is not True and total_prompt_tokens <= max_token_chars) or len(raw_data) == 1:
                # 数据量较小，直接使用原数据
                self.chat_question.data = data_str
                human_prompt = self.get_analysis_human_prompt()
                # 输入 field + data modify by huhuhuhr
                analysis_msg.append(HumanMessage(content=human_prompt))
            else:
                # 数据量大，需要进行分段摘要处理
                if self.chat_question.every is True:
                    # 当 every 为 True 时，不进行分片处理，直接使用全部数据
                    chunks = self._chunk_data_every(raw_data)
                    # 超过10条逐条分析，则进行分片处理
                    if len(chunks) > 10:
                        chunks = self._chunk_data_by_tokens(raw_data, max_token_chars)
                else:
                    # 否则进行分片处理
                    chunks = self._chunk_data_by_tokens(raw_data, max_token_chars)
                # 数据量大，需要进行逐条分析处理
                remark = f"正在进行分析...请耐心等待。分片数量:{len(chunks)}\n\n"
                yield {'content': "", 'reasoning_content': remark}
                every_chunk_max_token_chars = max_token_chars / len(chunks)
                for i, chunk in enumerate(chunks):
                    chunk_str = orjson.dumps(chunk).decode()
                    # 流式处理摘要生成
                    remark = f"\n第{i + 1}段数据,归纳内容(生成中...)\n\n"
                    yield {'content': "", 'reasoning_content': remark}
                    for summary in self._summarize_data_chunk(chunk_str,
                                                              i + 1,
                                                              len(chunks),
                                                              every_chunk_max_token_chars,
                                                              self.chat_question.question):
                        if summary.get("partial"):
                            # 流式返回部分摘要
                            yield {'content': "", 'reasoning_content': summary.get('summary')}
                        elif summary.get("error"):
                            yield {'content': "", 'reasoning_content': summary.get('summary')}
                        else:
                            final_summary = summary.get('summary')
                            analysis_msg.append(HumanMessage(content=f"第{i + 1}段数据分析结果:{final_summary}"))
                            yield {'content': "", 'reasoning_content': "\n"}
        else:
            self.chat_question.data = orjson.dumps([]).decode()
            human_prompt = self.get_analysis_human_prompt()
            # 输入 field + data modify by huhuhuhr
            analysis_msg.append(HumanMessage(content=human_prompt))

        self.current_logs[OperationEnum.ANALYSIS] = start_log(session=_session,
                                                              ai_modal_id=self.chat_question.ai_modal_id,
                                                              ai_modal_name=self.chat_question.ai_modal_name,
                                                              operate=OperationEnum.ANALYSIS,
                                                              record_id=self.record.id,
                                                              full_message=[
                                                                  {'type': msg.type,
                                                                   'content': msg.content} for
                                                                  msg
                                                                  in analysis_msg])
        full_thinking_text = ''
        full_analysis_text = ''
        # modify by huhuhuhr 打印分析
        self.print_Message(analysis_msg)
        token_usage = {}
        res = process_stream(self.stream_with_think(self.llm.stream(analysis_msg)), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_analysis_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

        analysis_msg.append(AIMessage(full_analysis_text))

        self.current_logs[OperationEnum.ANALYSIS] = end_log(session=_session,
                                                            log=self.current_logs[
                                                                OperationEnum.ANALYSIS],
                                                            full_message=[
                                                                {'type': msg.type,
                                                                 'content': msg.content}
                                                                for msg in analysis_msg],
                                                            reasoning_content=full_thinking_text,
                                                            token_usage=token_usage)
        self.record = save_analysis_answer(session=_session, record_id=self.record.id,
                                           answer=orjson.dumps({'content': full_analysis_text}).decode())

    def generate_predict(self, _session: Session):
        fields = self.get_fields_from_chart(_session)
        self.chat_question.fields = orjson.dumps(fields).decode()
        data = get_chat_chart_data(_session, self.record.id)
        self.chat_question.data = orjson.dumps(data.get('data')).decode()

        if SQLBotLicenseUtil.valid():
            ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None
            self.chat_question.custom_prompt = find_custom_prompts(_session, CustomPromptTypeEnum.PREDICT_DATA,
                                                                   self.current_user.oid, ds_id)

        predict_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        predict_msg.append(SystemMessage(content=self.chat_question.predict_sys_question()))
        predict_msg.append(HumanMessage(content=self.chat_question.predict_user_question()))

        self.current_logs[OperationEnum.PREDICT_DATA] = start_log(session=_session,
                                                                  ai_modal_id=self.chat_question.ai_modal_id,
                                                                  ai_modal_name=self.chat_question.ai_modal_name,
                                                                  operate=OperationEnum.PREDICT_DATA,
                                                                  record_id=self.record.id,
                                                                  full_message=[
                                                                      {'type': msg.type,
                                                                       'content': msg.content} for
                                                                      msg
                                                                      in predict_msg])
        full_thinking_text = ''
        full_predict_text = ''
        token_usage = {}
        # modify by huhuhuhr
        res = process_stream(self.stream_with_think(self.llm.stream(predict_msg)), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_predict_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

        predict_msg.append(AIMessage(full_predict_text))
        self.record = save_predict_answer(session=_session, record_id=self.record.id,
                                          answer=orjson.dumps({'content': full_predict_text}).decode())
        self.current_logs[OperationEnum.PREDICT_DATA] = end_log(session=_session,
                                                                log=self.current_logs[
                                                                    OperationEnum.PREDICT_DATA],
                                                                full_message=[
                                                                    {'type': msg.type,
                                                                     'content': msg.content}
                                                                    for msg in predict_msg],
                                                                reasoning_content=full_thinking_text,
                                                                token_usage=token_usage)

    def generate_recommend_questions_task(self, _session: Session):

        # get schema
        if self.ds and not self.chat_question.db_schema:
            self.chat_question.db_schema = self.out_ds_instance.get_db_schema(
                self.ds.id, self.chat_question.question) if self.out_ds_instance else get_table_schema(
                session=_session,
                current_user=self.current_user, ds=self.ds,
                question=self.chat_question.question,
                embedding=False)

        guess_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        guess_msg.append(SystemMessage(content=self.chat_question.guess_sys_question()))

        old_questions = list(map(lambda q: q.strip(), get_old_questions(_session, self.record.datasource)))
        guess_msg.append(
            HumanMessage(content=self.chat_question.guess_user_question(orjson.dumps(old_questions).decode())))

        self.current_logs[OperationEnum.GENERATE_RECOMMENDED_QUESTIONS] = start_log(session=_session,
                                                                                    ai_modal_id=self.chat_question.ai_modal_id,
                                                                                    ai_modal_name=self.chat_question.ai_modal_name,
                                                                                    operate=OperationEnum.GENERATE_RECOMMENDED_QUESTIONS,
                                                                                    record_id=self.record.id,
                                                                                    full_message=[
                                                                                        {'type': msg.type,
                                                                                         'content': msg.content} for
                                                                                        msg
                                                                                        in guess_msg])
        full_thinking_text = ''
        full_guess_text = ''
        token_usage = {}
        # modify by huhuhuhr
        res = process_stream(self.stream_with_think(self.llm.stream(guess_msg)), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_guess_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

        guess_msg.append(AIMessage(full_guess_text))

        self.current_logs[OperationEnum.GENERATE_RECOMMENDED_QUESTIONS] = end_log(session=_session,
                                                                                  log=self.current_logs[
                                                                                      OperationEnum.GENERATE_RECOMMENDED_QUESTIONS],
                                                                                  full_message=[
                                                                                      {'type': msg.type,
                                                                                       'content': msg.content}
                                                                                      for msg in guess_msg],
                                                                                  reasoning_content=full_thinking_text,
                                                                                  token_usage=token_usage)
        self.record = save_recommend_question_answer(session=_session, record_id=self.record.id,
                                                     answer={'content': full_guess_text})

        yield {'recommended_question': self.record.recommended_question}

    def select_datasource(self, _session: Session):
        datasource_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        datasource_msg.append(SystemMessage(self.chat_question.datasource_sys_question()))
        if self.current_assistant and self.current_assistant.type != 4:
            _ds_list = get_assistant_ds(session=_session, llm_service=self)
        else:
            stmt = select(CoreDatasource.id, CoreDatasource.name, CoreDatasource.description).where(
                and_(CoreDatasource.oid == self.current_user.oid))
            _ds_list = [
                {
                    "id": ds.id,
                    "name": ds.name,
                    "description": ds.description
                }
                for ds in _session.exec(stmt)
            ]
        if not _ds_list:
            raise SingleMessageError('No available datasource configuration found')
        ignore_auto_select = _ds_list and len(_ds_list) == 1
        # ignore auto select ds

        full_thinking_text = ''
        full_text = ''
        if not ignore_auto_select:
            if settings.TABLE_EMBEDDING_ENABLED and (
                    not self.current_assistant or (self.current_assistant and self.current_assistant.type != 1)):
                _ds_list = get_ds_embedding(_session, self.current_user, _ds_list, self.out_ds_instance,
                                            self.chat_question.question, self.current_assistant)
                # yield {'content': '{"id":' + str(ds.get('id')) + '}'}

            _ds_list_dict = []
            for _ds in _ds_list:
                _ds_list_dict.append(_ds)
            datasource_msg.append(
                HumanMessage(self.chat_question.datasource_user_question(orjson.dumps(_ds_list_dict).decode())))

            self.current_logs[OperationEnum.CHOOSE_DATASOURCE] = start_log(session=_session,
                                                                           ai_modal_id=self.chat_question.ai_modal_id,
                                                                           ai_modal_name=self.chat_question.ai_modal_name,
                                                                           operate=OperationEnum.CHOOSE_DATASOURCE,
                                                                           record_id=self.record.id,
                                                                           full_message=[{'type': msg.type,
                                                                                          'content': msg.content}
                                                                                         for
                                                                                         msg in datasource_msg])

            token_usage = {}
            # modify by huhuhuhr
            res = process_stream(self.stream_with_think(self.llm.stream(datasource_msg)), token_usage)
            for chunk in res:
                if chunk.get('content'):
                    full_text += chunk.get('content')
                if chunk.get('reasoning_content'):
                    full_thinking_text += chunk.get('reasoning_content')
                yield chunk
            datasource_msg.append(AIMessage(full_text))

            self.current_logs[OperationEnum.CHOOSE_DATASOURCE] = end_log(session=_session,
                                                                         log=self.current_logs[
                                                                             OperationEnum.CHOOSE_DATASOURCE],
                                                                         full_message=[
                                                                             {'type': msg.type,
                                                                              'content': msg.content}
                                                                             for msg in datasource_msg],
                                                                         reasoning_content=full_thinking_text,
                                                                         token_usage=token_usage)

            json_str = extract_nested_json(full_text)
            if json_str is None:
                raise SingleMessageError(f'Cannot parse datasource from answer: {full_text}')
            ds = orjson.loads(json_str)

        _error: Exception | None = None
        _datasource: int | None = None
        _engine_type: str | None = None
        try:
            data: dict = _ds_list[0] if ignore_auto_select else ds

            if data.get('id') and data.get('id') != 0:
                _datasource = data['id']
                _chat = _session.get(Chat, self.record.chat_id)
                _chat.datasource = _datasource
                if self.current_assistant and self.current_assistant.type in dynamic_ds_types:
                    _ds = self.out_ds_instance.get_ds(data['id'])
                    self.ds = _ds
                    self.chat_question.engine = _ds.type + get_version(self.ds)
                    self.chat_question.db_schema = self.out_ds_instance.get_db_schema(self.ds.id,
                                                                                      self.chat_question.question)
                    _engine_type = self.chat_question.engine
                    _chat.engine_type = _ds.type
                else:
                    _ds = _session.get(CoreDatasource, _datasource)
                    if not _ds:
                        _datasource = None
                        raise SingleMessageError(f"Datasource configuration with id {_datasource} not found")
                    self.ds = CoreDatasource(**_ds.model_dump())
                    self.chat_question.engine = (_ds.type_name if _ds.type != 'excel' else 'PostgreSQL') + get_version(
                        self.ds)
                    self.chat_question.db_schema = get_table_schema(session=_session,
                                                                    current_user=self.current_user, ds=self.ds,
                                                                    question=self.chat_question.question)
                    _engine_type = self.chat_question.engine
                    _chat.engine_type = _ds.type_name
                # save chat
                with _session.begin_nested():
                    # 为了能继续记日志，先单独处理下事务
                    try:
                        _session.add(_chat)
                        _session.flush()
                        _session.refresh(_chat)
                        _session.commit()
                    except Exception as e:
                        _session.rollback()
                        raise e

            elif data['fail']:
                raise SingleMessageError(data['fail'])
            else:
                raise SingleMessageError('No available datasource configuration found')

        except Exception as e:
            _error = e

        if not ignore_auto_select and not settings.TABLE_EMBEDDING_ENABLED:
            self.record = save_select_datasource_answer(session=_session, record_id=self.record.id,
                                                        answer=orjson.dumps({'content': full_text}).decode(),
                                                        datasource=_datasource,
                                                        engine_type=_engine_type)
        if self.ds:
            oid = self.ds.oid if isinstance(self.ds, CoreDatasource) else 1
            ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None

            self.chat_question.terminologies = get_terminology_template(_session, self.chat_question.question, oid,
                                                                        ds_id)
            if self.current_assistant and self.current_assistant.type == 1:
                self.chat_question.data_training = get_training_template(_session, self.chat_question.question,
                                                                         oid, None, self.current_assistant.id)
            else:
                self.chat_question.data_training = get_training_template(_session, self.chat_question.question,
                                                                         oid, ds_id)
            if SQLBotLicenseUtil.valid():
                self.chat_question.custom_prompt = find_custom_prompts(_session, CustomPromptTypeEnum.GENERATE_SQL,
                                                                       oid, ds_id)
            # midify by huorong
            self.init_messages(_session=_session)

        if _error:
            raise _error

    def generate_sql(self, _session: Session):
        # append current question
        self.sql_message.append(HumanMessage(
            self.chat_question.sql_user_question(current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),change_title = self.change_title)))

        self.current_logs[OperationEnum.GENERATE_SQL] = start_log(session=_session,
                                                                  ai_modal_id=self.chat_question.ai_modal_id,
                                                                  ai_modal_name=self.chat_question.ai_modal_name,
                                                                  operate=OperationEnum.GENERATE_SQL,
                                                                  record_id=self.record.id,
                                                                  full_message=[
                                                                      {'type': msg.type, 'content': msg.content} for msg
                                                                      in self.sql_message])
        full_thinking_text = ''
        full_sql_text = ''
        token_usage = {}
        # modify by huhuhuhr huhuhuhr
        self.print_Message(self.sql_message)
        res = process_stream(self.stream_with_think(self.llm.stream(self.sql_message)), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_sql_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

        self.sql_message.append(AIMessage(full_sql_text))

        self.current_logs[OperationEnum.GENERATE_SQL] = end_log(session=_session,
                                                                log=self.current_logs[OperationEnum.GENERATE_SQL],
                                                                full_message=[{'type': msg.type, 'content': msg.content}
                                                                              for msg in self.sql_message],
                                                                reasoning_content=full_thinking_text,
                                                                token_usage=token_usage)
        self.record = save_sql_answer(session=_session, record_id=self.record.id,
                                      answer=orjson.dumps({'content': full_sql_text}).decode())

    def generate_with_sub_sql(self, session: Session, sql, sub_mappings: list):
        sub_query = json.dumps(sub_mappings, ensure_ascii=False)
        self.chat_question.sql = sql
        self.chat_question.sub_query = sub_query
        dynamic_sql_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        dynamic_sql_msg.append(SystemMessage(content=self.chat_question.dynamic_sys_question()))
        dynamic_sql_msg.append(HumanMessage(content=self.chat_question.dynamic_user_question()))

        self.current_logs[OperationEnum.GENERATE_DYNAMIC_SQL] = start_log(session=session,
                                                                          ai_modal_id=self.chat_question.ai_modal_id,
                                                                          ai_modal_name=self.chat_question.ai_modal_name,
                                                                          operate=OperationEnum.GENERATE_DYNAMIC_SQL,
                                                                          record_id=self.record.id,
                                                                          full_message=[{'type': msg.type,
                                                                                         'content': msg.content}
                                                                                        for
                                                                                        msg in dynamic_sql_msg])

        full_thinking_text = ''
        full_dynamic_text = ''
        token_usage = {}
        # modify by huhuhuhr
        res = process_stream(self.stream_with_think(self.llm.stream(dynamic_sql_msg)), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_dynamic_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')

        dynamic_sql_msg.append(AIMessage(full_dynamic_text))

        self.current_logs[OperationEnum.GENERATE_DYNAMIC_SQL] = end_log(session=session,
                                                                        log=self.current_logs[
                                                                            OperationEnum.GENERATE_DYNAMIC_SQL],
                                                                        full_message=[
                                                                            {'type': msg.type,
                                                                             'content': msg.content}
                                                                            for msg in dynamic_sql_msg],
                                                                        reasoning_content=full_thinking_text,
                                                                        token_usage=token_usage)

        SQLBotLogUtil.info(full_dynamic_text)
        return full_dynamic_text

    def generate_assistant_dynamic_sql(self, _session: Session, sql, tables: List):
        ds: AssistantOutDsSchema = self.ds
        sub_query = []
        result_dict = {}
        for table in ds.tables:
            if table.name in tables and table.sql:
                # sub_query.append({"table": table.name, "query": table.sql})
                result_dict[table.name] = table.sql
                sub_query.append({"table": table.name, "query": f'{dynamic_subsql_prefix}{table.name}'})
        if not sub_query:
            return None
        temp_sql_text = self.generate_with_sub_sql(session=_session, sql=sql, sub_mappings=sub_query)
        result_dict['sqlbot_temp_sql_text'] = temp_sql_text
        return result_dict

    def build_table_filter(self, session: Session, sql: str, filters: list):
        filter = json.dumps(filters, ensure_ascii=False)
        self.chat_question.sql = sql
        self.chat_question.filter = filter
        permission_sql_msg: List[Union[BaseMessage, dict[str, Any]]] = []
        permission_sql_msg.append(SystemMessage(content=self.chat_question.filter_sys_question()))
        permission_sql_msg.append(HumanMessage(content=self.chat_question.filter_user_question()))

        self.current_logs[OperationEnum.GENERATE_SQL_WITH_PERMISSIONS] = start_log(session=session,
                                                                                   ai_modal_id=self.chat_question.ai_modal_id,
                                                                                   ai_modal_name=self.chat_question.ai_modal_name,
                                                                                   operate=OperationEnum.GENERATE_SQL_WITH_PERMISSIONS,
                                                                                   record_id=self.record.id,
                                                                                   full_message=[
                                                                                       {'type': msg.type,
                                                                                        'content': msg.content} for
                                                                                       msg
                                                                                       in permission_sql_msg])
        full_thinking_text = ''
        full_filter_text = ''
        token_usage = {}
        # modify by huhuhuhr
        res = process_stream(self.stream_with_think(self.llm.stream(permission_sql_msg)), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_filter_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')

        permission_sql_msg.append(AIMessage(full_filter_text))

        self.current_logs[OperationEnum.GENERATE_SQL_WITH_PERMISSIONS] = end_log(session=session,
                                                                                 log=self.current_logs[
                                                                                     OperationEnum.GENERATE_SQL_WITH_PERMISSIONS],
                                                                                 full_message=[
                                                                                     {'type': msg.type,
                                                                                      'content': msg.content}
                                                                                     for msg in permission_sql_msg],
                                                                                 reasoning_content=full_thinking_text,
                                                                                 token_usage=token_usage)

        SQLBotLogUtil.info(full_filter_text)
        return full_filter_text

    def generate_filter(self, _session: Session, sql: str, tables: List):
        filters = get_row_permission_filters(session=_session, current_user=self.current_user, ds=self.ds,
                                             tables=tables)
        if not filters:
            return None
        return self.build_table_filter(session=_session, sql=sql, filters=filters)

    def generate_assistant_filter(self, _session: Session, sql, tables: List):
        ds: AssistantOutDsSchema = self.ds
        filters = []
        for table in ds.tables:
            if table.name in tables and table.rule:
                filters.append({"table": table.name, "filter": table.rule})
        if not filters:
            return None
        return self.build_table_filter(session=_session, sql=sql, filters=filters)

    def generate_chart(self, _session: Session, chart_type: Optional[str] = ''):
        # append current question
        self.chart_message.append(HumanMessage(self.chat_question.chart_user_question(chart_type)))

        self.current_logs[OperationEnum.GENERATE_CHART] = start_log(session=_session,
                                                                    ai_modal_id=self.chat_question.ai_modal_id,
                                                                    ai_modal_name=self.chat_question.ai_modal_name,
                                                                    operate=OperationEnum.GENERATE_CHART,
                                                                    record_id=self.record.id,
                                                                    full_message=[
                                                                        {'type': msg.type, 'content': msg.content} for
                                                                        msg
                                                                        in self.chart_message])
        full_thinking_text = ''
        full_chart_text = ''
        token_usage = {}
        # modify by huhuhuhr
        res = process_stream(self.stream_with_think(self.llm.stream(self.chart_message)), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_chart_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

        self.chart_message.append(AIMessage(full_chart_text))

        self.record = save_chart_answer(session=_session, record_id=self.record.id,
                                        answer=orjson.dumps({'content': full_chart_text}).decode())
        self.current_logs[OperationEnum.GENERATE_CHART] = end_log(session=_session,
                                                                  log=self.current_logs[OperationEnum.GENERATE_CHART],
                                                                  full_message=[
                                                                      {'type': msg.type, 'content': msg.content}
                                                                      for msg in self.chart_message],
                                                                  reasoning_content=full_thinking_text,
                                                                  token_usage=token_usage)

    @staticmethod
    def check_sql(res: str) -> tuple[str, Optional[list]]:
        json_str = extract_nested_json(res)
        if json_str is None:
            raise SingleMessageError(orjson.dumps({'message': 'Cannot parse sql from answer',
                                                   'traceback': "Cannot parse sql from answer:\n" + res}).decode())
        sql: str
        data: dict
        try:
            data = orjson.loads(json_str)

            if data['success']:
                sql = data['sql']
            else:
                message = data['message']
                raise SingleMessageError(message)
        except SingleMessageError as e:
            raise e
        except Exception:
            raise SingleMessageError(orjson.dumps({'message': 'Cannot parse sql from answer',
                                                   'traceback': "Cannot parse sql from answer:\n" + res}).decode())

        if sql.strip() == '':
            raise SingleMessageError("SQL query is empty")
        return sql, data.get('tables')

    @staticmethod
    def get_chart_type_from_sql_answer(res: str) -> Optional[str]:
        json_str = extract_nested_json(res)
        if json_str is None:
            return None

        chart_type: Optional[str]
        data: dict
        try:
            data = orjson.loads(json_str)

            if data['success']:
                chart_type = data['chart-type']
            else:
                return None
        except Exception:
            return None

        return chart_type

    @staticmethod
    def get_brief_from_sql_answer(res: str) -> Optional[str]:
        json_str = extract_nested_json(res)
        if json_str is None:
            return None

        brief: Optional[str]
        data: dict
        try:
            data = orjson.loads(json_str)

            if data['success']:
                brief = data['brief']
            else:
                return None
        except Exception:
            return None

        return brief

    def check_save_sql(self, session: Session, res: str) -> str:
        sql, *_ = self.check_sql(res=res)
        save_sql(session=session, sql=sql, record_id=self.record.id)

        self.chat_question.sql = sql

        return sql

    def check_save_chart(self, session: Session, res: str) -> Dict[str, Any]:

        json_str = extract_nested_json(res)
        if json_str is None:
            raise SingleMessageError(orjson.dumps({'message': 'Cannot parse chart config from answer',
                                                   'traceback': "Cannot parse chart config from answer:\n" + res}).decode())
        data: dict

        chart: Dict[str, Any] = {}
        message = ''
        error = False

        try:
            data = orjson.loads(json_str)
            if data['type'] and data['type'] != 'error':
                # todo type check
                chart = data
                if chart.get('columns'):
                    for v in chart.get('columns'):
                        v['value'] = v.get('value').lower()
                if chart.get('axis'):
                    if chart.get('axis').get('x'):
                        chart.get('axis').get('x')['value'] = chart.get('axis').get('x').get('value').lower()
                    if chart.get('axis').get('y'):
                        chart.get('axis').get('y')['value'] = chart.get('axis').get('y').get('value').lower()
                    if chart.get('axis').get('series'):
                        chart.get('axis').get('series')['value'] = chart.get('axis').get('series').get('value').lower()
            elif data['type'] == 'error':
                message = data['reason']
                error = True
            else:
                raise Exception('Chart is empty')
        except Exception:
            error = True
            message = orjson.dumps({'message': 'Cannot parse chart config from answer',
                                    'traceback': "Cannot parse chart config from answer:\n" + res}).decode()

        if error:
            raise SingleMessageError(message)

        save_chart(session=session, chart=orjson.dumps(chart).decode(), record_id=self.record.id)

        return chart

    def check_save_predict_data(self, session: Session, res: str) -> bool:

        json_str = extract_nested_json(res)

        if not json_str:
            json_str = ''

        save_predict_data(session=session, record_id=self.record.id, data=json_str)

        if json_str == '':
            return False

        return True

    def save_error(self, session: Session, message: str):
        return save_error_message(session=session, record_id=self.record.id, message=message)

    def save_sql_data(self, session: Session, data_obj: Dict[str, Any]):
        try:
            data_result = data_obj.get('data')
            limit = 1000
            if data_result:
                data_result = prepare_for_orjson(data_result)
                if data_result and len(data_result) > limit and settings.GENERATE_SQL_QUERY_LIMIT_ENABLED:
                    data_obj['data'] = data_result[:limit]
                    data_obj['limit'] = limit
                else:
                    data_obj['data'] = data_result
            return save_sql_exec_data(session=session, record_id=self.record.id,
                                      data=orjson.dumps(data_obj).decode())
        except Exception as e:
            raise e

    def finish(self, session: Session):
        return finish_record(session=session, record_id=self.record.id)

    def execute_sql(self, sql: str):
        """Execute SQL query

        Args:
            ds: Data source instance
            sql: SQL query statement

        Returns:
            Query results
        """
        SQLBotLogUtil.info(f"Executing SQL on ds_id {self.ds.id}: {sql}")
        try:
            return exec_sql(ds=self.ds, sql=sql, origin_column=False)
        except Exception as e:
            if isinstance(e, ParseSQLResultError):
                raise e
            else:
                err = traceback.format_exc(limit=1, chain=True)
                raise SQLBotDBError(err)

    def pop_chunk(self):
        try:
            chunk = self.chunk_list.pop(0)
            return chunk
        except IndexError as e:
            return None

    def await_result(self):
        while self.is_running():
            while True:
                chunk = self.pop_chunk()
                if chunk is not None:
                    yield chunk
                else:
                    break
        while True:
            chunk = self.pop_chunk()
            if chunk is None:
                break
            yield chunk

    def run_task_async(self, in_chat: bool = True, stream: bool = True,
                       finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART):
        if in_chat:
            stream = True
        self.future = executor.submit(self.run_task_cache, in_chat, stream, finish_step)

    def run_task_cache(self, in_chat: bool = True, stream: bool = True,
                       finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART):
        for chunk in self.run_task(in_chat, stream, finish_step):
            self.chunk_list.append(chunk)

    def run_task(self, in_chat: bool = True, stream: bool = True,
                 finish_step: ChatFinishStep = ChatFinishStep.GENERATE_CHART):
        json_result: Dict[str, Any] = {'success': True}
        _session = None
        try:
            _session = session_maker()
            if self.ds:
                oid = self.ds.oid if isinstance(self.ds, CoreDatasource) else 1
                ds_id = self.ds.id if isinstance(self.ds, CoreDatasource) else None
                self.chat_question.terminologies = get_terminology_template(_session, self.chat_question.question,
                                                                            oid, ds_id)
                if self.current_assistant and self.current_assistant.type == 1:
                    self.chat_question.data_training = get_training_template(_session, self.chat_question.question,
                                                                             oid, None, self.current_assistant.id)
                else:
                    self.chat_question.data_training = get_training_template(_session, self.chat_question.question,
                                                                             oid, ds_id)
                if SQLBotLicenseUtil.valid():
                    self.chat_question.custom_prompt = find_custom_prompts(_session,
                                                                           CustomPromptTypeEnum.GENERATE_SQL,
                                                                       oid, ds_id)
                # modify by huhuhuhr
                self.init_messages(_session=_session)

            # return id
            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'id', 'id': self.get_record().id}).decode() + '\n\n'
            if not stream:
                json_result['record_id'] = self.get_record().id

                # select datasource if datasource is none
            if not self.ds:
                ds_res = self.select_datasource(_session)

                for chunk in ds_res:
                    SQLBotLogUtil.info(chunk)
                    if in_chat:
                        yield 'data:' + orjson.dumps(
                            {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                             'type': 'datasource-result'}).decode() + '\n\n'
                if in_chat:
                    yield 'data:' + orjson.dumps({'id': self.ds.id, 'datasource_name': self.ds.name,
                                                  'engine_type': self.ds.type_name or self.ds.type,
                                                  'type': 'datasource'}).decode() + '\n\n'

                self.chat_question.db_schema = self.out_ds_instance.get_db_schema(
                    self.ds.id, self.chat_question.question) if self.out_ds_instance else get_table_schema(
                    session=_session,
                    current_user=self.current_user,
                    ds=self.ds,
                    question=self.chat_question.question)
            else:
                self.validate_history_ds(_session)

            # check connection
            connected = check_connection(ds=self.ds, trans=None)
            if not connected:
                raise SQLBotDBConnectionError('Connect DB failed')

            # modify by huhuhuhr
            if self.chat_question.my_sql is not None and self.chat_question.my_sql.strip() != '':
                sql_res = self.generate_sql_with_sql(_session=_session)
            else:
                sql_res = self.generate_sql(_session=_session)

            full_sql_text = ''
            for chunk in sql_res:
                full_sql_text += chunk.get('content')
                if in_chat:
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                         'type': 'sql-result'}).decode() + '\n\n'
            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'info', 'msg': 'sql generated'}).decode() + '\n\n'
            # filter sql
            SQLBotLogUtil.info(full_sql_text)

            chart_type = self.get_chart_type_from_sql_answer(full_sql_text)

            # return title
            if self.change_title:
                llm_brief = self.get_brief_from_sql_answer(full_sql_text)
                if (llm_brief and llm_brief != '')  or (self.chat_question.question and self.chat_question.question.strip() != ''):
                    save_brief = llm_brief if (llm_brief and llm_brief != '') else self.chat_question.question.strip()[:20]
                    brief = rename_chat(session=_session,
                                        rename_object=RenameChat(id=self.get_record().chat_id,
                                                                 brief=save_brief))
                    if in_chat:
                        yield 'data:' + orjson.dumps({'type': 'brief', 'brief': brief}).decode() + '\n\n'
                    if not stream:
                        json_result['title'] = brief

            use_dynamic_ds: bool = self.current_assistant and self.current_assistant.type in dynamic_ds_types
            is_page_embedded: bool = self.current_assistant and self.current_assistant.type == 4
            dynamic_sql_result = None
            sqlbot_temp_sql_text = None
            assistant_dynamic_sql = None
            # row permission
            if ((not self.current_assistant or is_page_embedded) and is_normal_user(
                    self.current_user)) or use_dynamic_ds:
                sql, tables = self.check_sql(res=full_sql_text)
                sql_result = None

                if use_dynamic_ds:
                    dynamic_sql_result = self.generate_assistant_dynamic_sql(_session, sql, tables)
                    sqlbot_temp_sql_text = dynamic_sql_result.get(
                        'sqlbot_temp_sql_text') if dynamic_sql_result else None
                    # sql_result = self.generate_assistant_filter(sql, tables)
                else:
                    sql_result = self.generate_filter(_session, sql, tables)  # maybe no sql and tables

                if sql_result:
                    SQLBotLogUtil.info(sql_result)
                    sql = self.check_save_sql(session=_session, res=sql_result)
                elif dynamic_sql_result and sqlbot_temp_sql_text:
                    assistant_dynamic_sql = self.check_save_sql(session=_session, res=sqlbot_temp_sql_text)
                else:
                    sql = self.check_save_sql(session=_session, res=full_sql_text)
            else:
                # modify by huhuhuhr
                SQLBotLogUtil.info(full_sql_text)
                sql = self.check_save_sql(session=_session, res=full_sql_text)

            SQLBotLogUtil.info('sql: ' + sql)

            if not stream:
                json_result['sql'] = sql

            format_sql = sqlparse.format(sql, reindent=True)
            if in_chat:
                yield 'data:' + orjson.dumps({'content': format_sql, 'type': 'sql'}).decode() + '\n\n'
            else:
                if stream:
                    yield f'```sql\n{format_sql}\n```\n\n'

            # execute sql
            real_execute_sql = sql
            if sqlbot_temp_sql_text and assistant_dynamic_sql:
                dynamic_sql_result.pop('sqlbot_temp_sql_text')
                for origin_table, subsql in dynamic_sql_result.items():
                    assistant_dynamic_sql = assistant_dynamic_sql.replace(f'{dynamic_subsql_prefix}{origin_table}',
                                                                          subsql)
                real_execute_sql = assistant_dynamic_sql

            if finish_step.value <= ChatFinishStep.GENERATE_SQL.value:
                if in_chat:
                    yield 'data:' + orjson.dumps({'type': 'finish'}).decode() + '\n\n'
                if not stream:
                    yield json_result
                return

            result = self.execute_sql(sql=real_execute_sql)

            _data = DataFormat.convert_large_numbers_in_object_array(result.get('data'))
            result["data"] = _data

            self.save_sql_data(session=_session, data_obj=result)
            if in_chat:
                yield 'data:' + orjson.dumps({'content': 'execute-success', 'type': 'sql-data'}).decode() + '\n\n'
            if not stream:
                json_result['data'] = get_chat_chart_data(_session, self.record.id)

            if finish_step.value <= ChatFinishStep.QUERY_DATA.value:
                if stream:
                    if in_chat:
                        yield 'data:' + orjson.dumps({'type': 'finish'}).decode() + '\n\n'
                    else:
                        _column_list = []
                        for field in result.get('fields'):
                            _column_list.append(AxisObj(name=field, value=field))

                        md_data, _fields_list = DataFormat.convert_object_array_for_pandas(_column_list, result.get('data'))

                        # data, _fields_list, col_formats = self.format_pd_data(_column_list, result.get('data'))

                        if not _data or not _fields_list:
                            yield 'The SQL execution result is empty.\n\n'
                        else:
                            df = pd.DataFrame(_data, columns=_fields_list)
                            df_safe = DataFormat.safe_convert_to_string(df)
                            markdown_table = df_safe.to_markdown(index=False)
                            yield markdown_table + '\n\n'
                else:
                    yield json_result
                return

            # generate chart
            chart_res = self.generate_chart(_session, chart_type)
            full_chart_text = ''
            for chunk in chart_res:
                full_chart_text += chunk.get('content')
                if in_chat:
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                         'type': 'chart-result'}).decode() + '\n\n'
            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'info', 'msg': 'chart generated'}).decode() + '\n\n'

            # filter chart
            SQLBotLogUtil.info(full_chart_text)
            chart = self.check_save_chart(session=_session, res=full_chart_text)
            SQLBotLogUtil.info(chart)

            if not stream:
                json_result['chart'] = chart

            if in_chat:
                yield 'data:' + orjson.dumps(
                    {'content': orjson.dumps(chart).decode(), 'type': 'chart'}).decode() + '\n\n'
            else:
                if stream:
                    _fields = {}
                    if chart.get('columns'):
                        for _column in chart.get('columns'):
                            if _column:
                                _fields[_column.get('value')] = _column.get('name')
                    if chart.get('axis'):
                        if chart.get('axis').get('x'):
                            _fields[chart.get('axis').get('x').get('value')] = chart.get('axis').get('x').get('name')
                        if chart.get('axis').get('y'):
                            _fields[chart.get('axis').get('y').get('value')] = chart.get('axis').get('y').get('name')
                        if chart.get('axis').get('series'):
                            _fields[chart.get('axis').get('series').get('value')] = chart.get('axis').get('series').get(
                                'name')
                    _column_list = []
                    for field in result.get('fields'):
                        _column_list.append(
                            AxisObj(name=field if not _fields.get(field) else _fields.get(field), value=field))

                    md_data, _fields_list = DataFormat.convert_object_array_for_pandas(_column_list, result.get('data'))

                    # data, _fields_list, col_formats = self.format_pd_data(_column_list, result.get('data'))

                    if not md_data or not _fields_list:
                        yield 'The SQL execution result is empty.\n\n'
                    else:
                        df = pd.DataFrame(md_data, columns=_fields_list)
                        df_safe = DataFormat.safe_convert_to_string(df)
                        markdown_table = df_safe.to_markdown(index=False)
                        yield markdown_table + '\n\n'

            if in_chat:
                yield 'data:' + orjson.dumps({'type': 'finish'}).decode() + '\n\n'
            else:
                # todo generate picture
                try:
                    if chart['type'] != 'table':
                        yield '### generated chart picture\n\n'
                        image_url = request_picture(self.record.chat_id, self.record.id, chart,
                                                    format_json_data(result))
                        SQLBotLogUtil.info(image_url)
                        if stream:
                            yield f'![{chart["type"]}]({image_url})'
                        else:
                            json_result['image_url'] = image_url
                except Exception as e:
                    if stream:
                        raise e

            if not stream:
                yield json_result

        except Exception as e:
            traceback.print_exc()
            error_msg: str
            if isinstance(e, SingleMessageError):
                error_msg = str(e)
            elif isinstance(e, SQLBotDBConnectionError):
                error_msg = orjson.dumps(
                    {'message': str(e), 'type': 'db-connection-err'}).decode()
            elif isinstance(e, SQLBotDBError):
                error_msg = orjson.dumps(
                    {'message': 'Execute SQL Failed', 'traceback': str(e), 'type': 'exec-sql-err'}).decode()
            else:
                error_msg = orjson.dumps({'message': str(e), 'traceback': traceback.format_exc(limit=1)}).decode()
            if _session:
                self.save_error(session=_session, message=error_msg)
            if in_chat:
                yield 'data:' + orjson.dumps({'content': error_msg, 'type': 'error'}).decode() + '\n\n'
            else:
                if stream:
                    yield f'> &#x274c; **ERROR**\n\n> \n\n> {error_msg}。'
                else:
                    json_result['success'] = False
                    json_result['message'] = error_msg
                    yield json_result
        finally:
            self.finish(_session)
            session_maker.remove()



    def run_recommend_questions_task_async(self):
        self.future = executor.submit(self.run_recommend_questions_task_cache)

    def run_recommend_questions_task_cache(self):
        for chunk in self.run_recommend_questions_task():
            self.chunk_list.append(chunk)

    def run_recommend_questions_task(self):
        try:
            _session = session_maker()
            res = self.generate_recommend_questions_task(_session)

            for chunk in res:
                if chunk.get('recommended_question'):
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('recommended_question'),
                         'type': 'recommended_question'}).decode() + '\n\n'
                else:
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                         'type': 'recommended_question_result'}).decode() + '\n\n'
        except Exception:
            traceback.print_exc()
        finally:
            session_maker.remove()

    # modify by huhuhuhr
    def run_analysis_or_predict_task_async(self, session: Session, action_type: str, base_record: ChatRecord
                                           , dataStr: str = None, payload: AnalysisIntentPayload = None):
        self.set_record(save_analysis_predict_record(session, base_record, action_type))
        # modify by huhuhuhr
        self.future = executor.submit(self.run_analysis_or_predict_task_cache, action_type
                                      , dataStr, payload)

    # modify by huhuhuhr
    def run_analysis_or_predict_task_cache(self, action_type: str
                                           , dataStr: str = None, payload: AnalysisIntentPayload = None):
        for chunk in self.run_analysis_or_predict_task(action_type, dataStr, payload):
            self.chunk_list.append(chunk)

    # modify by huhuhuhr
    def run_analysis_or_predict_task(self, action_type: str
                                     , dataStr: str = None, payload: AnalysisIntentPayload = None):
        _session = None
        try:
            _session = session_maker()
            yield 'data:' + orjson.dumps({'type': 'id', 'id': self.get_record().id}).decode() + '\n\n'

            if action_type == 'analysis':
                analysis_res = self.generate_analysis(dataStr=dataStr, payload=payload, _session=_session)
                for chunk in analysis_res:
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                         'type': 'analysis-result'}).decode() + '\n\n'
                yield 'data:' + orjson.dumps({'type': 'info', 'msg': 'analysis generated'}).decode() + '\n\n'

                yield 'data:' + orjson.dumps({'type': 'analysis_finish'}).decode() + '\n\n'

            elif action_type == 'predict':
                # generate predict
                analysis_res = self.generate_predict(_session)
                full_text = ''
                for chunk in analysis_res:
                    yield 'data:' + orjson.dumps(
                        {'content': chunk.get('content'), 'reasoning_content': chunk.get('reasoning_content'),
                         'type': 'predict-result'}).decode() + '\n\n'
                    full_text += chunk.get('content')
                yield 'data:' + orjson.dumps({'type': 'info', 'msg': 'predict generated'}).decode() + '\n\n'

                _data = self.check_save_predict_data(session=_session, res=full_text)
                if _data:
                    yield 'data:' + orjson.dumps({'type': 'predict-success'}).decode() + '\n\n'
                else:
                    yield 'data:' + orjson.dumps({'type': 'predict-failed'}).decode() + '\n\n'

                yield 'data:' + orjson.dumps({'type': 'predict_finish'}).decode() + '\n\n'

            self.finish(_session)
        except Exception as e:
            error_msg: str
            if isinstance(e, SingleMessageError):
                error_msg = str(e)
            else:
                error_msg = orjson.dumps({'message': str(e), 'traceback': traceback.format_exc(limit=1)}).decode()
            if _session:
                self.save_error(session=_session, message=error_msg)
            yield 'data:' + orjson.dumps({'content': error_msg, 'type': 'error'}).decode() + '\n\n'
        finally:
            # end
            session_maker.remove()

    def validate_history_ds(self, session: Session):
        _ds = self.ds
        if not self.current_assistant or self.current_assistant.type == 4:
            try:
                current_ds = session.get(CoreDatasource, _ds.id)
                if not current_ds:
                    raise SingleMessageError('chat.ds_is_invalid')
            except Exception as e:
                raise SingleMessageError("chat.ds_is_invalid")
        else:
            try:
                _ds_list: list[dict] = get_assistant_ds(session=session, llm_service=self)
                match_ds = any(item.get("id") == _ds.id for item in _ds_list)
                if not match_ds:
                    type = self.current_assistant.type
                    msg = f"[please check ds list and public ds list]" if type == 0 else f"[please check ds api]"
                    raise SingleMessageError(msg)
            except Exception as e:
                raise SingleMessageError(f"ds is invalid [{str(e)}]")

    # modify by huhuhuhr
    def count_tokens(self, text) -> int:
        """返回文本的 token 数量（int），失败时返回字符长度作为估算"""
        if not isinstance(text, str) or text == "":
            return max(0, len(str(text)) if str(text) != "None" else 0)

        try:
            if self._encoder is not None:
                return len(self._encoder.encode(text))
            else:
                # 备用：临时加载（仅在全局失败时）
                return len(tiktoken.get_encoding("o200k_base").encode(text))
        except Exception:
            return len(text)

    # modify by huhuhuhr
    def get_analysis_human_prompt(self):
        if self.chat_question.my_schema is not None:
            human_prompt = self.chat_question.analysis_user_question_with_schema(self.chat_question.my_schema)
        else:
            human_prompt = self.chat_question.analysis_user_question()
        return human_prompt

    # modify by huhuhuhr
    def get_analysis_sys_prompt(self, payload):
        if self.chat_question.my_promote is not None:
            sys_prompt = self.get_my_sys_prompt(payload)
        elif payload is not None:
            sys_prompt = analysis_question(role=payload.role, task=payload.task, intent=payload.intent,
                                           terminologies=self.chat_question.terminologies)
        else:
            sys_prompt = self.chat_question.analysis_sys_question()
        return sys_prompt

    # modify by huhuhuhr
    def get_my_sys_prompt(self, payload, _session: Session):
        # 术语 modify by huhuhuhr
        if self.chat_question is not None and self.chat_question.terminologies is not None and self.chat_question.terminologies != '':
            self.chat_question.terminologies = get_terminology_template(_session,
                                                                        self.chat_question.question,
                                                                        self.current_user.oid)
        template_vars = {
            "role": getattr(payload, 'role', '') if payload else '',
            "task": getattr(payload, 'task', '') if payload else '',
            "intent": getattr(payload, 'intent', '') if payload else '',
            "terminologies": getattr(self.chat_question, 'terminologies', '')
        }
        # 使用 Template 安全替换
        template = Template(self.chat_question.my_promote)
        sys_prompt = template.safe_substitute(**template_vars)
        return sys_prompt

    # modify by huhuhuhr
    def _chunk_data_by_tokens(self, data: List[Any], max_tokens: int) -> List[List[Any]]:
        """
        根据 token 数量将数据分块，每块不超过 max_tokens。

        Args:
            data: 数据列表，每个 item 可被 orjson 序列化
            max_tokens: 每块最大 token 数

        Returns:
            分块后的数据列表
        """
        chunks = []
        current_chunk = []
        current_tokens = 0

        for item in data:
            item_str = orjson.dumps(item).decode('utf-8')
            item_token_count = self.count_tokens(item_str)

            # 单个 item 超长？至少让它单独成块（避免丢失）
            if item_token_count > max_tokens:
                SQLBotLogUtil.warning(
                    f"单条数据项 token 数 ({item_token_count}) 超过限制 ({max_tokens})，将单独成块: {str(item)[:100]}..."
                )
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_tokens = 0
                chunks.append([item])  # 单独成块
                continue

            # 如果加进去会超限，且当前块非空，则保存当前块
            if current_tokens + item_token_count > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = [item]
                current_tokens = item_token_count
            else:
                current_chunk.append(item)
                current_tokens += item_token_count

        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _chunk_data_every(self, data: List[Any]) -> List[List[Any]]:
        """
        根据 token 数量将数据分块，每块不超过 max_tokens。

        Args:
            data: 数据列表，每个 item 可被 orjson 序列化

        Returns:
            分块后的数据列表
        """
        chunks = []
        for item in data:
            chunks.append([item])

        return chunks

    # modify by huhuhuhr
    def model_think_parse(self, chunks: Iterator[BaseMessageChunk]) -> Iterator[BaseMessageChunk]:
        THINK_BEGIN_TAG = "<think>"
        THINK_END_TAG = "</think>"
        response_content = ""
        force_think_begin = False
        tag_begin = False
        think_begin = True if force_think_begin else False
        think_end = False

        for chunk in chunks:
            SQLBotLogUtil.info(f"original chunk:{chunk}")
            if (chunk.additional_kwargs and hasattr(chunk.additional_kwargs, "reasoning_content")
                    and chunk.additional_kwargs["reasoning_content"] is not None and chunk.additional_kwargs[
                        "reasoning_content"] != ''):
                yield chunk
                continue
            token = chunk.content
            # 分次处理输入字符，以缓冲的为准，防止连续的 < 符号判断导致丢失 tag 的前部分，导致出错，如 <\n</|th|in|k>
            if "<" in token:
                tag_begin = True
                response_content = ""

            if tag_begin:
                response_content += token
                if not force_think_begin and not think_begin and THINK_BEGIN_TAG in response_content:
                    think_begin = True
                    tag_begin = False
                elif not think_end and THINK_END_TAG in response_content:
                    # 返回 think 结束之前的内容
                    end_index = response_content.index(THINK_END_TAG) + len(THINK_END_TAG)
                    chunk.additional_kwargs["reasoning_content"] = response_content[:end_index]
                    chunk.content = ''
                    yield chunk
                    think_end = True
                    tag_begin = False
                    # 返回 think 结束之后的内容（如果有）
                    response_content = response_content[end_index:]
                    if response_content == "":
                        continue
                # 去除 < 符号之前的字符，防止 < 符号之前有其他字符导致判断出错
                elif (response_content[response_content.index("<"):] not in THINK_BEGIN_TAG
                      and response_content[response_content.index("<"):] not in THINK_END_TAG):
                    tag_begin = False

            if tag_begin:
                continue

            if response_content == "":
                response_content = token
            if response_content == "":
                continue

            if think_begin and not think_end:
                chunk.additional_kwargs["reasoning_content"] = response_content
                chunk.content = ''
                yield chunk
            else:
                chunk.content = response_content
                yield chunk
            response_content = ""

    # modify by huhuhuhr
    def stream_with_think(self, raw_stream: Iterator[BaseMessageChunk]) -> Iterator[BaseMessageChunk]:
        for chunk in self.model_think_parse(raw_stream):
            SQLBotLogUtil.debug(f"stream_with_think-chunk:{chunk}")
            yield chunk

    # modify by huhuhuhr
    def _summarize_data_chunk(self, chunk_data_str, chunk_index, total_chunks, limits_token_usage, question):
        """
        使用LLM对数据块进行摘要，明确要求使用中文回答
        """
        try:
            # 构建摘要提示，明确要求使用中文
            summary_prompt = [
                SystemMessage(
                    content=f"你是一个数据分析师。你的任务是对给定的数据块提供简洁的中文摘要。重点关注关键模式、趋势、统计信息和重要观察。保持摘要信息丰富但简洁，必须使用中文回复。总结字数不要超过{int(limits_token_usage)}个字。内容总结需要符合用户的预期，用户问题：{question}。"),
                HumanMessage(
                    content=f"{chunk_data_str}\n\n请用中文提供此数据块的简洁摘要。")
            ]

            # 生成摘要（流式）
            full_summary = ""
            res = self.stream_with_think(self.llm.stream(summary_prompt))
            for chunk in res:
                SQLBotLogUtil.info(f"_summarize_data_chunk:{chunk}")
                full_summary += chunk.content
                # 流式返回当前生成的部分摘要
                yield {
                    "chunk_index": chunk_index,
                    "total_chunks": total_chunks,
                    "summary": chunk.content,
                    "partial": True
                }

            # 返回完整摘要
            yield {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "summary": full_summary,
                "partial": False
            }
        except Exception as e:
            # 如果摘要生成失败，返回错误信息
            yield {
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
                "summary": f"生成数据块 {chunk_index} 的摘要时出错: {str(e)}\n",
                "error": True
            }

    # modify by huhuhuhr
    def generate_sql_with_sql(self, _session: Session):
        # append current question
        self.sql_message.append(HumanMessage(
            self.chat_question.sql_user_question(current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))))
        # 硬设置提示词
        content = orjson.dumps({
            "question": self.chat_question.question,
            "sql": self.chat_question.my_sql
        }).decode()
        self.sql_message.append(HumanMessage(content=content))
        # add at 20250619 huhuhuhr
        self.print_Message(self.sql_message)

        self.current_logs[OperationEnum.GENERATE_SQL] = start_log(session=_session,
                                                                  ai_modal_id=self.chat_question.ai_modal_id,
                                                                  ai_modal_name=self.chat_question.ai_modal_name,
                                                                  operate=OperationEnum.GENERATE_SQL,
                                                                  record_id=self.record.id,
                                                                  full_message=[
                                                                      {'type': msg.type, 'content': msg.content} for
                                                                      msg
                                                                      in self.sql_message])
        full_thinking_text = ''
        full_sql_text = ''
        token_usage = {}
        res = process_stream(self.stream_with_think(self.llm.stream(self.sql_message)), token_usage)
        for chunk in res:
            if chunk.get('content'):
                full_sql_text += chunk.get('content')
            if chunk.get('reasoning_content'):
                full_thinking_text += chunk.get('reasoning_content')
            yield chunk

        self.sql_message.append(AIMessage(full_sql_text))

        self.current_logs[OperationEnum.GENERATE_SQL] = end_log(session=_session,
                                                                log=self.current_logs[OperationEnum.GENERATE_SQL],
                                                                full_message=[
                                                                    {'type': msg.type, 'content': msg.content}
                                                                    for msg in self.sql_message],
                                                                reasoning_content=full_thinking_text,
                                                                token_usage=token_usage)
        self.record = save_sql_answer(session=_session, record_id=self.record.id,
                                      answer=orjson.dumps({'content': full_sql_text}).decode())

    # modify by huhuhuhr
    def print_Message(self, messages=None):
        if messages is None:
            messages = self.sql_message
        for i, msg in enumerate(messages):
            if isinstance(msg, SystemMessage):
                SQLBotLogUtil.info(f"\n\nSystem prompt [{i}]:\n {msg.content}\n")
            elif isinstance(msg, HumanMessage):
                SQLBotLogUtil.info(f"\nHuman prompt [{i}]:\n {msg.content}\n")
            elif isinstance(msg, AIMessage):
                SQLBotLogUtil.info(f"\nAI prompt [{i}]:\n {msg.content}\n\n")


def execute_sql_with_db(db: SQLDatabase, sql: str) -> str:
    """Execute SQL query using SQLDatabase

    Args:
        db: SQLDatabase instance
        sql: SQL query statement

    Returns:
        str: Query results formatted as string
    """
    try:
        # Execute query
        result = db.run(sql)

        if not result:
            return "Query executed successfully but returned no results."

        # Format results
        return str(result)

    except Exception as e:
        error_msg = f"SQL execution failed: {str(e)}"
        SQLBotLogUtil.exception(error_msg)
        raise RuntimeError(error_msg)


def request_picture(chat_id: int, record_id: int, chart: dict, data: dict):
    file_name = f'c_{chat_id}_r_{record_id}'

    columns = chart.get('columns') if chart.get('columns') else []
    x = None
    y = None
    series = None
    if chart.get('axis'):
        x = chart.get('axis').get('x')
        y = chart.get('axis').get('y')
        series = chart.get('axis').get('series')

    axis = []
    for v in columns:
        axis.append({'name': v.get('name'), 'value': v.get('value')})
    if x:
        axis.append({'name': x.get('name'), 'value': x.get('value'), 'type': 'x'})
    if y:
        axis.append({'name': y.get('name'), 'value': y.get('value'), 'type': 'y'})
    if series:
        axis.append({'name': series.get('name'), 'value': series.get('value'), 'type': 'series'})

    request_obj = {
        "path": os.path.join(settings.MCP_IMAGE_PATH, file_name),
        "type": chart['type'],
        "data": orjson.dumps(data.get('data') if data.get('data') else []).decode(),
        "axis": orjson.dumps(axis).decode(),
    }

    requests.post(url=settings.MCP_IMAGE_HOST, json=request_obj)

    request_path = urllib.parse.urljoin(settings.SERVER_IMAGE_HOST, f"{file_name}.png")

    return request_path


def get_token_usage(chunk: BaseMessageChunk, token_usage: dict = None):
    try:
        if chunk.usage_metadata:
            if token_usage is None:
                token_usage = {}
            token_usage['input_tokens'] = chunk.usage_metadata.get('input_tokens')
            token_usage['output_tokens'] = chunk.usage_metadata.get('output_tokens')
            token_usage['total_tokens'] = chunk.usage_metadata.get('total_tokens')
    except Exception:
        pass


def process_stream(res: Iterator[BaseMessageChunk],
                   token_usage: Dict[str, Any] = None,
                   enable_tag_parsing: bool = settings.PARSE_REASONING_BLOCK_ENABLED,
                   start_tag: str = settings.DEFAULT_REASONING_CONTENT_START,
                   end_tag: str = settings.DEFAULT_REASONING_CONTENT_END
                   ):
    if token_usage is None:
        token_usage = {}
    in_thinking_block = False  # 标记是否在思考过程块中
    current_thinking = ''  # 当前收集的思考过程内容
    pending_start_tag = ''  # 用于缓存可能被截断的开始标签部分

    for chunk in res:
        SQLBotLogUtil.info(f"process_stream chunk:{chunk}")
        reasoning_content_chunk = ''
        content = chunk.content
        output_content = ''  # 实际要输出的内容

        # 检查additional_kwargs中的reasoning_content
        if 'reasoning_content' in chunk.additional_kwargs:
            reasoning_content = chunk.additional_kwargs.get('reasoning_content', '')
            if reasoning_content is None:
                reasoning_content = ''

            # 累积additional_kwargs中的思考内容到current_thinking
            current_thinking += reasoning_content
            reasoning_content_chunk = reasoning_content

        # 只有当current_thinking不是空字符串时才跳过标签解析
        if not in_thinking_block and current_thinking.strip() != '':
            output_content = content  # 正常输出content
            yield {
                'content': output_content,
                'reasoning_content': reasoning_content_chunk
            }
            get_token_usage(chunk, token_usage)
            continue  # 跳过后续的标签解析逻辑

        # 如果没有有效的思考内容，并且启用了标签解析，才执行标签解析逻辑
        # 如果有缓存的开始标签部分，先拼接当前内容
        if pending_start_tag:
            content = pending_start_tag + content
            pending_start_tag = ''

        # 检查是否开始思考过程块（处理可能被截断的开始标签）
        if enable_tag_parsing and not in_thinking_block and start_tag:
            if start_tag in content:
                start_idx = content.index(start_tag)
                # 只有当开始标签前面没有其他文本时才认为是真正的思考块开始
                if start_idx == 0 or content[:start_idx].strip() == '':
                    # 完整标签存在且前面没有其他文本
                    output_content += content[:start_idx]  # 输出开始标签之前的内容
                    content = content[start_idx + len(start_tag):]  # 移除开始标签
                    in_thinking_block = True
                else:
                    # 开始标签前面有其他文本，不认为是思考块开始
                    output_content += content
                    content = ''
            else:
                # 检查是否可能有部分开始标签
                for i in range(1, len(start_tag)):
                    if content.endswith(start_tag[:i]):
                        # 只有当当前内容全是空白时才缓存部分标签
                        if content[:-i].strip() == '':
                            pending_start_tag = start_tag[:i]
                            content = content[:-i]  # 移除可能的部分标签
                            output_content += content
                            content = ''
                        break

        # 处理思考块内容
        if enable_tag_parsing and in_thinking_block and end_tag:
            if end_tag in content:
                # 找到结束标签
                end_idx = content.index(end_tag)
                current_thinking += content[:end_idx]  # 收集思考内容
                reasoning_content_chunk += current_thinking  # 添加到当前块的思考内容
                content = content[end_idx + len(end_tag):]  # 移除结束标签后的内容
                current_thinking = ''  # 重置当前思考内容
                in_thinking_block = False
                output_content += content  # 输出结束标签之后的内容
            else:
                # 在遇到结束标签前，持续收集思考内容
                current_thinking += content
                reasoning_content_chunk += content
                content = ''

        else:
            # 不在思考块中或标签解析未启用，正常输出
            output_content += content

        yield {
            'content': output_content,
            'reasoning_content': reasoning_content_chunk
        }
        get_token_usage(chunk, token_usage)


def get_lang_name(lang: str):
    if not lang:
        return '简体中文'
    normalized = lang.lower()
    if normalized.startswith('en'):
        return '英文'
    if normalized.startswith('ko'):
        return '韩语'
    return '简体中文'
