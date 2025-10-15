import asyncio
import io
import traceback

import orjson
import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select

from apps.chat.curd.chat import list_chats, get_chat_with_records, create_chat, rename_chat, \
    delete_chat, get_chat_chart_data, get_chat_predict_data, get_chat_with_records_with_data, get_chat_record_by_id, \
    format_json_data
from apps.chat.models.chat_model import CreateChat, ChatRecord, RenameChat, ChatQuestion, ExcelData
from apps.chat.task.llm import LLMService
from common.core.deps import CurrentAssistant, SessionDep, CurrentUser, Trans

router = APIRouter(tags=["Data Q&A"], prefix="/chat")


@router.get("/list")
async def chats(session: SessionDep, current_user: CurrentUser):
    return list_chats(session, current_user)


@router.get("/{chart_id}")
async def get_chat(session: SessionDep, current_user: CurrentUser, chart_id: int, current_assistant: CurrentAssistant):
    def inner():
        return get_chat_with_records(chart_id=chart_id, session=session, current_user=current_user,
                                     current_assistant=current_assistant)

    return await asyncio.to_thread(inner)


@router.get("/{chart_id}/with_data")
async def get_chat_with_data(session: SessionDep, current_user: CurrentUser, chart_id: int,
                             current_assistant: CurrentAssistant):
    def inner():
        return get_chat_with_records_with_data(chart_id=chart_id, session=session, current_user=current_user,
                                               current_assistant=current_assistant)

    return await asyncio.to_thread(inner)


@router.get("/record/{chart_record_id}/data")
async def chat_record_data(session: SessionDep, chart_record_id: int):
    def inner():
        data = get_chat_chart_data(chart_record_id=chart_record_id, session=session)
        return format_json_data(data)

    return await asyncio.to_thread(inner)


@router.get("/record/{chart_record_id}/predict_data")
async def chat_predict_data(session: SessionDep, chart_record_id: int):
    def inner():
        data = get_chat_predict_data(chart_record_id=chart_record_id, session=session)
        return format_json_data(data)

    return await asyncio.to_thread(inner)


@router.post("/rename")
async def rename(session: SessionDep, chat: RenameChat):
    try:
        return rename_chat(session=session, rename_object=chat)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.delete("/{chart_id}")
async def delete(session: SessionDep, chart_id: int):
    try:
        return delete_chat(session=session, chart_id=chart_id)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/start")
async def start_chat(session: SessionDep, current_user: CurrentUser, create_chat_obj: CreateChat):
    try:
        return create_chat(session, current_user, create_chat_obj)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/assistant/start")
async def start_chat(session: SessionDep, current_user: CurrentUser):
    try:
        return create_chat(session, current_user, CreateChat(origin=2), False)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/recommend_questions/{chat_record_id}")
async def recommend_questions(session: SessionDep, current_user: CurrentUser, chat_record_id: int,
                              current_assistant: CurrentAssistant):
    def _return_empty():
        yield 'data:' + orjson.dumps({'content': '[]', 'type': 'recommended_question'}).decode() + '\n\n'

    try:
        record = get_chat_record_by_id(session, chat_record_id)

        if not record:
            return StreamingResponse(_return_empty(), media_type="text/event-stream")

        request_question = ChatQuestion(chat_id=record.chat_id, question=record.question if record.question else '')

        llm_service = await LLMService.create(session, current_user, request_question, current_assistant, True)
        llm_service.set_record(record)
        llm_service.run_recommend_questions_task_async()
    except Exception as e:
        traceback.print_exc()

        def _err(_e: Exception):
            yield 'data:' + orjson.dumps({'content': str(_e), 'type': 'error'}).decode() + '\n\n'

        return StreamingResponse(_err(e), media_type="text/event-stream")

    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")


@router.post("/question")
async def stream_sql(session: SessionDep, current_user: CurrentUser, request_question: ChatQuestion,
                     current_assistant: CurrentAssistant):
    """Stream SQL analysis results
    
    Args:
        session: Database session
        current_user: CurrentUser
        request_question: User question model
        
    Returns:
        Streaming response with analysis results
    """

    try:
        llm_service = await LLMService.create(session, current_user, request_question, current_assistant,
                                              embedding=True)
        llm_service.init_record(session=session)
        llm_service.run_task_async()
    except Exception as e:
        traceback.print_exc()

        def _err(_e: Exception):
            yield 'data:' + orjson.dumps({'content': str(_e), 'type': 'error'}).decode() + '\n\n'

        return StreamingResponse(_err(e), media_type="text/event-stream")

    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")


@router.post("/record/{chat_record_id}/{action_type}")
async def analysis_or_predict(session: SessionDep, current_user: CurrentUser, chat_record_id: int, action_type: str,
                              current_assistant: CurrentAssistant):
    try:
        if action_type != 'analysis' and action_type != 'predict':
            raise Exception(f"Type {action_type} Not Found")
        record: ChatRecord | None = None

        stmt = select(ChatRecord.id, ChatRecord.question, ChatRecord.chat_id, ChatRecord.datasource,
                      ChatRecord.engine_type,
                      ChatRecord.ai_modal_id, ChatRecord.create_by, ChatRecord.chart, ChatRecord.data).where(
            and_(ChatRecord.id == chat_record_id))
        result = session.execute(stmt)
        for r in result:
            record = ChatRecord(id=r.id, question=r.question, chat_id=r.chat_id, datasource=r.datasource,
                                engine_type=r.engine_type, ai_modal_id=r.ai_modal_id, create_by=r.create_by,
                                chart=r.chart,
                                data=r.data)

        if not record:
            raise Exception(f"Chat record with id {chat_record_id} not found")

        if not record.chart:
            raise Exception(
                f"Chat record with id {chat_record_id} has not generated chart, do not support to analyze it")

        request_question = ChatQuestion(chat_id=record.chat_id, question=record.question)

        llm_service = await LLMService.create(session, current_user, request_question, current_assistant)
        llm_service.run_analysis_or_predict_task_async(session, action_type, record)
    except Exception as e:
        traceback.print_exc()

        def _err(_e: Exception):
            yield 'data:' + orjson.dumps({'content': str(_e), 'type': 'error'}).decode() + '\n\n'

        return StreamingResponse(_err(e), media_type="text/event-stream")

    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")


@router.post("/excel/export")
async def export_excel(excel_data: ExcelData, trans: Trans):
    def inner():
        _fields_list = []
        data = []
        if not excel_data.data:
            raise HTTPException(
                status_code=500,
                detail=trans("i18n_excel_export.data_is_empty")
            )

        # 预处理数据并记录每列的格式类型
        col_formats = {}  # 格式类型：'text'（文本）、'number'（数字）、'default'（默认）
        for field_idx, field in enumerate(excel_data.axis):
            _fields_list.append(field.name)
            col_formats[field_idx] = 'default'  # 默认不特殊处理

        for _data in excel_data.data:
            _row = []
            for field_idx, field in enumerate(excel_data.axis):
                value = _data.get(field.value)
                if value is not None:
                    # 检查是否为数字且需要特殊处理
                    if isinstance(value, (int, float)):
                        # 整数且超过15位 → 转字符串并标记为文本列
                        if isinstance(value, int) and len(str(abs(value))) > 15:
                            value = str(value)
                            col_formats[field_idx] = 'text'
                        # 小数且超过15位有效数字 → 转字符串并标记为文本列
                        elif isinstance(value, float):
                            decimal_str = format(value, '.16f').rstrip('0').rstrip('.')
                            if len(decimal_str) > 15:
                                value = str(value)
                                col_formats[field_idx] = 'text'
                        # 其他数字列标记为数字格式（避免科学记数法）
                        elif col_formats[field_idx] != 'text':
                            col_formats[field_idx] = 'number'
                _row.append(value)
            data.append(_row)

        df = pd.DataFrame(data, columns=_fields_list)

        buffer = io.BytesIO()

        with pd.ExcelWriter(buffer, engine='xlsxwriter',
                            engine_kwargs={'options': {'strings_to_numbers': False}}) as writer:
            df.to_excel(writer, sheet_name='Sheet1', index=False)

            # 获取 xlsxwriter 的工作簿和工作表对象
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']

            for col_idx, fmt_type in col_formats.items():
                if fmt_type == 'text':
                    worksheet.set_column(col_idx, col_idx, None, workbook.add_format({'num_format': '@'}))
                elif fmt_type == 'number':
                    worksheet.set_column(col_idx, col_idx, None, workbook.add_format({'num_format': '0'}))

        buffer.seek(0)
        return io.BytesIO(buffer.getvalue())

    result = await asyncio.to_thread(inner)
    return StreamingResponse(result, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
