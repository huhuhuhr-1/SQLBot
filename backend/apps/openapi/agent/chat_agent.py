import json
import traceback

import orjson
from fastapi import HTTPException
from sqlmodel import Session

from apps.chat.models.chat_model import ChatRecord
from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id, bind_datasource
from apps.openapi.models.openapiModels import DataSourceRequest, OpenChatQuestion, \
    IntentPayload, AnalysisIntentPayload
from apps.openapi.service.openapi_llm import LLMService
from apps.openapi.service.openapi_service import chat_identify_intent, get_chat_record, analysis_identify_intent
from common.core.db import get_session
from common.core.deps import CurrentUser, CurrentAssistant
from common.utils.utils import SQLBotLogUtil


class ChatAgent:
    def __init__(self
                 , session: Session,
                 current_user: CurrentUser,
                 chat_question: OpenChatQuestion,
                 current_assistant: CurrentAssistant
                 ):
        self.current_user = current_user
        self.chat_question = chat_question
        self.current_assistant = current_assistant
        self.task_type = self.chat_question.task_type
        self.no_reasoning_flag = self.chat_question.no_reasoning

        self.record = None
        self.llm_service = None
        self.payload = None
        self.data_str = None
        self.datasource = None
        self.session = session

    async def run_analysis_or_predict(self):
        try:
            self.record = await self.get_record()
            self.llm_service = await LLMService.create(
                session=self.session,
                current_user=self.current_user,
                chat_question=self.chat_question,
                current_assistant=self.current_assistant)
            self.payload = self.get_predict_or_analysis_payload()
            self.data_str = self.get_data_str()

            self.llm_service.run_analysis_or_predict_task_async(self.task_type,
                                                                self.record,
                                                                self.data_str,
                                                                self.payload)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    async def run_chat(self):
        self.datasource = await self.get_datasource()
        self.llm_service = await LLMService.create(
            self.session,
            self.current_user,
            self.chat_question,
            self.current_assistant,
            no_reasoning=self.no_reasoning_flag,
            embedding=True
        )
        self.payload = self.get_chat_payload()

        # 初始化聊天记录
        self.llm_service.init_record(self.session)

        # 异步运行任务
        self.llm_service.run_task_async()
        stream = self.llm_service.await_result()

        return stream

    def get_chat_payload(self):
        """获取对话时意图识别的结果"""
        payload = None

        # 如果存在意图检测，则进行意图识别
        if self.chat_question.intent:
            payload = chat_identify_intent(self.llm_service.llm, self.chat_question.question)

        # 记录意图识别结果
        if payload:
            SQLBotLogUtil.info(f"意图识别详情 - 原始输入: '{self.chat_question.question}', "
                               f"搜索意图: '{payload.search}', "
                               f"分析意图: '{payload.analysis}', "
                               f"预测意图: '{payload.predict}'")
        else:
            SQLBotLogUtil.info(
                f"未识别到意图 - 输入: '{self.chat_question.question}', 未识别到有效意图")

            if self.chat_question.analysis or self.chat_question.predict:
                payload = IntentPayload(
                    search=self.chat_question.question,
                    analysis=self.chat_question.question if self.chat_question.analysis else "",
                    predict=self.chat_question.question if self.chat_question.predict else ""
                )

        # 如果存在意图，则使用意图作为问题
        if payload is not None and payload.search != "":
            self.llm_service.chat_question.question = payload.search
        else:
            payload = None

        return payload

    async def get_datasource(self):
        """获取数据源信息并绑定到聊天会话"""
        datasource = None

        # 获取数据源信息
        for session in get_session():
            datasource = get_datasource_by_name_or_id(
                session=session,
                user=self.current_user,
                query=DataSourceRequest(id=self.chat_question.db_id)
            )
            if datasource:
                # 绑定数据源到聊天会话
                await bind_datasource(datasource,
                                      self.chat_question.chat_id,
                                      session,
                                      self.current_user)
                SQLBotLogUtil.info("绑定数据源成功")
                break
            else:
                SQLBotLogUtil.error("数据源未找到")
                raise HTTPException(
                    status_code=500,
                    detail="数据源未找到"
                )
        return datasource

    def get_data_str(self):
        data_str = None

        if self.chat_question.chat_data_object is not None:
            data_str = json.dumps(self.chat_question.chat_data_object, ensure_ascii=False)

        return data_str

    async def get_record(self):
        # 更新chat_id和question
        record = None

        if self.chat_question.chat_record_id is not None:
            chat_record_id = self.chat_question.chat_record_id

            for session in get_session():
                record = await get_chat_record(session, chat_record_id)

            if not record.chart:
                raise HTTPException(
                    status_code=500,
                    detail=f"Chat record with id {chat_record_id} has not generated chart, do not support to analyze it"
                )

            # 更新问题内容（如果提供）
            if self.chat_question.question:
                record.question = self.chat_question.question

            self.chat_question.chat_id = record.chat_id
            self.chat_question.question = record.question
        else:
            if not self.chat_question.chat_id or not self.chat_question.chat_data_object or not self.chat_question.db_id:
                raise HTTPException(
                    status_code=500,
                    detail=f"Chat record with chat_id or chat_data_object or db_id is not provided!"
                )
            record = ChatRecord()
            record.question = self.chat_question.question
            record.chat_id = self.chat_question.chat_id
            record.datasource = self.chat_question.db_id
            record.engine_type = ''
            record.ai_modal_id = -1
            record.create_by = -1
            record.chart = ''

            if isinstance(self.chat_question.chat_data_object, str):
                record.data = self.chat_question.chat_data_object
            else:
                record.data = orjson.dumps(self.chat_question.chat_data_object).decode()
            record.analysis_record_id = -1

            self.chat_question.chat_id = record.chat_id
            self.chat_question.question = record.question

        return record

    def get_predict_or_analysis_payload(self):
        try:
            payload = None

            if self.task_type == 'analysis':
                if self.chat_question.my_promote is None and self.chat_question.intent:
                    payload = analysis_identify_intent(self.llm_service.llm,
                                                       self.chat_question.question)
                # 记录意图识别结果
                if payload is None:
                    payload = AnalysisIntentPayload(
                        intent="分析",
                        role="数据分析师",
                        task=self.chat_question.question,
                    )
                SQLBotLogUtil.info(f"意图识别详情 - 原始输入: '{self.chat_question.question}', "
                                   f"意图: '{payload.intent}', "
                                   f"角色: '{payload.role}', "
                                   f"任务: '{payload.task}'")

            return payload
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )
