import asyncio
import contextvars
import csv
import hashlib
import io
import json
import os
import threading
import traceback
import uuid

import orjson
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import desc
from sqlmodel import select
from starlette.responses import FileResponse, HTMLResponse, StreamingResponse

from apps.ai_model.model_factory import create_llm
from apps.chat.curd.chat import (
    create_chat,
    delete_deep_analysis_chats_batch,
    get_chat_chart_data,
    get_chat_record_by_id,
    list_deep_analysis_chats,
)
from apps.chat.models.chat_model import Chat, ChatRecord, CreateChat
from apps.datasource.crud.datasource import (
    create_ds,
    get_datasource_list_for_openapi,
    get_datasource_list_for_openapi_excels,
    get_table_schema,
)
from apps.datasource.models.datasource import (
    CoreDatasource,
    CoreTable,
    CreateDatasource,
    DatasourceConf,
)
from apps.datasource.utils.utils import aes_encrypt
from apps.db.db import exec_sql
from apps.openapi.agent.chat_agent import ChatAgent
from apps.openapi.agent.data_agent import DataAgentRunner
from apps.openapi.agent.deep_analysis_graph import DeepAnalysisGraphRunner
from apps.openapi.agent.plan_agent import PlanAgent
from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id
from apps.openapi.models.openapiModels import (
    DataSourceRequest,
    DataSourceRequestWithSql,
    DatasourceResponse,
    DbBindChat,
    DeepAnalysisBatchDeleteRequest,
    DeepAnalysisRequest,
    OpenChat,
    OpenChatQuestion,
    OpenClean,
    OpenToken,
    SinglePgConfig,
    TokenRequest,
    common_headers,
)
from apps.openapi.service.openapi_db import (
    delete_ds,
    upload_excel_and_create_datasource_service,
)
from apps.openapi.service.openapi_llm import LLMService, get_lang_name
from apps.openapi.service.openapi_service import (
    _create_clean_response,
    _execute_cleanup,
    _get_chats_to_clean,
    _get_deep_analysis_chats_to_clean,
    _run_analysis_or_predict,
    create_access_token_with_expiry,
    is_safe_sql,
    merge_streaming_chunks,
)
from apps.system.crud.user import authenticate
from apps.system.schemas.system_schema import BaseUserDTO
from apps.template.template import get_base_template
from common.core.config import settings
from common.core.db import get_session
from common.core.deps import CurrentAssistant, CurrentUser, SessionDep, Trans
from common.error import ParseSQLResultError, SQLBotDBError
from common.utils.utils import SQLBotLogUtil

router = APIRouter(tags=["openapi"], prefix="/openapi")
path = settings.EXCEL_PATH


@router.get("/getAllTerminologiesByDataSource", summary="获取所有数据源的全部术语（按数据源分组）",
            description="返回：可见数据源列表 + 每个数据源的术语全量（不基于 question 命中）。",
            dependencies=[Depends(common_headers)])
async def get_all_terminologies_by_datasource(session: SessionDep, current_user: CurrentUser):
    from apps.datasource.crud.datasource import get_datasource_list_for_openapi
    from apps.terminology.curd.terminology import get_all_terminology_by_dslist

    datasources = get_datasource_list_for_openapi(session=session, user=current_user)

    terminologies_by_ds: dict[str, list[dict]] = {}
    for ds in datasources:
        terms = get_all_terminology_by_dslist(
            session=session,
            name=None,
            oid=current_user.oid if current_user.oid is not None else 1,
            dslist=[int(ds.id)],
        )
        terminologies_by_ds[str(ds.id)] = [t.model_dump() for t in terms]

    return {
        "data": {
            "datasources": [ds.model_dump() for ds in datasources],
            "terminologies_by_datasource": terminologies_by_ds,
        },
        "msg": None,
        "code": 0,
    }


@router.get("/exportAllTerminologiesByDataSource", summary="导出所有数据源术语（CSV）",
            description="将所有数据源的术语导出为一个 CSV 文件。",
            dependencies=[Depends(common_headers)])
async def export_all_terminologies_by_datasource(session: SessionDep, current_user: CurrentUser):
    from apps.datasource.crud.datasource import get_datasource_list_for_openapi
    from apps.terminology.curd.terminology import get_all_terminology_by_dslist

    datasources = get_datasource_list_for_openapi(session=session, user=current_user)

    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "datasource_id",
            "datasource_name",
            "word",
            "description",
            "other_words",
            "specific_ds",
            "datasource_ids",
            "enabled",
        ],
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()

    for ds in datasources:
        terms = get_all_terminology_by_dslist(
            session=session,
            name=None,
            oid=current_user.oid if current_user.oid is not None else 1,
            dslist=[int(ds.id)],
        )
        for t in terms:
            writer.writerow({
                "datasource_id": ds.id,
                "datasource_name": ds.name,
                "word": t.word,
                "description": t.description,
                "other_words": ",".join(t.other_words or []),
                "specific_ds": t.specific_ds,
                "datasource_ids": ",".join(map(str, t.datasource_ids or [])),
                "enabled": t.enabled,
            })

    csv_bytes = buf.getvalue().encode("utf-8-sig")
    filename = "terminologies_by_datasource.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _validate_and_resolve_openapi_sql_query(
    current_user: CurrentUser, request: DataSourceRequestWithSql
) -> tuple[CoreDatasource, str]:
    if not request.db_id:
        raise HTTPException(status_code=400, detail="db_id 参数不能为空")
    if not request.sql:
        raise HTTPException(status_code=400, detail="sql 参数不能为空")
    sanitized_sql = request.sql.strip()
    if not is_safe_sql(sanitized_sql):
        raise HTTPException(status_code=400, detail="SQL语句包含不安全的操作")
    datasource = None
    for session in get_session():
        try:
            datasource = get_datasource_by_name_or_id(
                session=session,
                user=current_user,
                query=DataSourceRequest(id=int(request.db_id)),
            )
            if datasource is None:
                raise HTTPException(status_code=500, detail="数据源未找到")
            break
        finally:
            session.close()
    return datasource, sanitized_sql


def _sql_result_to_csv_bytes(fields: list[str], rows: list[dict]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=fields,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fields})
    return buf.getvalue().encode("utf-8-sig")


@router.post("/getToken", summary="创建认证令牌",
             description="使用用户名和密码创建一个用于API认证的访问令牌")
async def get_token(
        session: SessionDep,
        trans: Trans,
        request: TokenRequest
) -> OpenToken:
    """
    创建认证令牌

    使用用户名和密码创建一个用于API认证的访问令牌。
    此接口遵循标准的认证流程，用于获取后续API调用所需的访问凭证。

    Args:
        session: 数据库会话依赖
        trans: 国际化翻译依赖
        request: 包含用户名和密码的请求体数据

    Returns:
        OpenToken: 包含访问令牌、过期时间和聊天ID的响应对象

    Raises:
        HTTPException: 当认证失败、用户无工作空间关联或用户被禁用时抛出400错误
    """
    # 验证用户身份
    user: BaseUserDTO = authenticate(
        session=session,
        account=request.username,
        password=request.password
    )

    # 验证用户状态
    from apps.openapi.service.openapi_service import validate_user_status
    validate_user_status(user, trans)

    # 创建访问令牌和过期时间
    access_token, expire_time = create_access_token_with_expiry(user.to_dict())

    # 处理聊天会话创建请求
    chat_id: int | None = None
    if request.create_chat:
        record = create_chat(session, user, CreateChat(origin=1), False)
        chat_id = record.id

    # 创建并返回访问令牌
    return OpenToken(
        access_token=f"bearer {access_token}",
        expire=expire_time,
        chat_id=chat_id
    )


@router.get("/getDataSourceList", summary="获取数据源列表",
            description="获取当前用户可访问的数据源列表",
            dependencies=[Depends(common_headers)])
async def get_data_source_list(session: SessionDep, user: CurrentUser):
    """
    获取数据源列表

    获取当前认证用户可访问的所有数据源列表。

    Args:
        session: 数据库会话依赖
        user: 当前认证用户信息

    Returns:
        用户可访问的数据源列表
    """
    return get_datasource_list_for_openapi(session=session, user=user)


@router.post("/getDataSourceByIdOrName", summary="根据ID或名称获取数据源",
             description="根据数据源ID或名称获取特定数据源信息",
             dependencies=[Depends(common_headers)],
             response_model=DatasourceResponse)
async def get_data_source_by_id_or_name(
        session: SessionDep,
        user: CurrentUser,
        request: DataSourceRequest
) -> DatasourceResponse:
    """
    根据ID或名称获取数据源

    根据数据源ID或名称获取特定数据源信息。

    Args:
        session: 数据库会话依赖
        user: 当前认证用户信息
        request: 数据源查询请求

    Returns:
        数据源信息
    """
    ds = get_datasource_by_name_or_id(session=session, user=user, query=request)
    if not ds:
        raise HTTPException(status_code=404, detail="数据源未找到")

    # 获取表结构
    from apps.datasource.crud.datasource import get_table_schema
    table_schema = get_table_schema(session=session, current_user=user, ds=ds, question="", embedding=False)

    # 获取术语
    from apps.terminology.curd.terminology import get_terminology_template
    terminologies_str, _ = get_terminology_template(session=session, question="", oid=user.oid, datasource=ds.id)

    # 构建响应
    res = DatasourceResponse.model_validate(ds.model_dump())
    res.table_schema = table_schema
    res.terminologies = terminologies_str
    return res


@router.post("/chat", summary="聊天",
             description="给定一个提示，模型将返回一条或多条预测消息",
             dependencies=[Depends(common_headers)])
async def chat(
        session: SessionDep,
        current_user: CurrentUser,
        chat_question: OpenChatQuestion,
        current_assistant: CurrentAssistant,
):
    """
    创建聊天完成（Create Chat Completion）

    给定一个对话历史和用户输入，模型将返回一条或多条预测消息。
    此接口遵循OpenAI Chat Completions API规范，支持流式响应。

    Args:
        session: 数据库连接
        current_user: 当前认证用户信息
        chat_question: 包含问题内容的请求对象
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应对象，包含模型生成的回复内容

    Raises:
        HTTPException: 当处理过程中出现异常时抛出500错误
    """
    try:
        # 传统sqlbot模式
        if chat_question.chat_mode != "plan":
            agent = ChatAgent(
                session=session,
                current_user=current_user,
                chat_question=chat_question,
                current_assistant=current_assistant)

            # predict or analysis
            if chat_question.task_type != "chat":
                await agent.run_analysis_or_predict()
                return StreamingResponse(agent.llm_service.await_result(), media_type="text/event-stream")
            # chat
            else:
                stream = await agent.run_chat()

                # 返回经过合并处理的流式响应
                return StreamingResponse(
                    merge_streaming_chunks(stream=stream,
                                           llm_service=agent.llm_service,
                                           payload=agent.payload,
                                           chat_question=agent.chat_question,
                                           session=session),
                    media_type="text/event-stream"
                )
        # plan模式
        else:
            queue = asyncio.Queue()
            llm = await create_llm()

            async def _stream(queue):
                try:
                    while True:
                        try:
                            # 使用带超时的get，避免无限阻塞
                            data = await asyncio.wait_for(queue.get(), timeout=1.0)
                        except asyncio.TimeoutError:
                            # 超时后检查队列状态，如果队列为空则继续等待
                            continue

                        yield 'data:' + orjson.dumps(data).decode() + '\n\n'

                        # 检查是否收到finish类型，如果是则结束流式响应
                        if isinstance(data, dict) and data.get('type') == 'finish':
                            break
                        elif isinstance(data, dict) and data.get('type') == 'error':
                            # 遇到错误也结束
                            break
                        else:
                            # 正常数据，继续循环
                            continue

                except GeneratorExit:
                    # 生成器被外部终止 - 使用return结束整个stream函数
                    return
                except Exception as e:
                    # 发送错误信息并结束 - 使用return结束整个stream函数
                    error_data = {
                        "type": "error",
                        "content": f"Stream error: {str(e)}"
                    }
                    yield 'data:' + orjson.dumps(error_data).decode() + '\n\n'
                    return

            def run_task(context,
                         current_user,
                         chat_question,
                         current_assistant,
                         queue):
                # 为子线程创建独立的数据库session，确保线程安全
                from common.core.db import get_db_session

                with get_db_session() as thread_session:
                    context.run(lambda: asyncio.run(
                        PlanAgent(
                            session=thread_session,
                            current_user=current_user,
                            chat_question=chat_question,
                            current_assistant=current_assistant,
                            queue=queue,
                            llm=llm).execute_plan()))

            thread = threading.Thread(target=run_task,
                                      args=(contextvars.copy_context(),
                                            current_user,
                                            chat_question,
                                            current_assistant, queue),
                                      daemon=True)
            thread.start()
            return StreamingResponse(
                _stream(queue),
                media_type="text/event-stream"
            )

    except Exception as e:
        # 记录异常信息用于调试
        SQLBotLogUtil.error(f"聊天接口异常: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"聊天处理失败: {str(e)}"
        )


async def to_async(gen):
    for item in gen:
        yield item


@router.post("/getData", dependencies=[Depends(common_headers)])
async def get_data(session: SessionDep, record_chat: OpenChat):
    """
    获取聊天记录数据

    根据聊天记录ID获取相关的图表数据。

    Args:
        session: 数据库会话依赖
        record_chat: 聊天对象，包含图表记录ID

    Returns:
        聊天记录对应的图表数据
    """

    def _fetch_chart_data() -> dict:
        """内部函数：执行数据库查询获取图表数据"""
        return get_chat_chart_data(
            chat_record_id=record_chat.chat_record_id,
            session=session
        )

    # 使用异步线程执行数据库查询
    return await asyncio.to_thread(_fetch_chart_data)


@router.post("/getDataByDbIdAndSql", dependencies=[Depends(common_headers)])
def get_data_by_db_id_and_sql(current_user: CurrentUser, request: DataSourceRequestWithSql):
    datasource, sanitized_sql = _validate_and_resolve_openapi_sql_query(current_user, request)
    SQLBotLogUtil.info(f"Executing SQL on ds_id {request.db_id}: {request.sql}")
    try:
        return exec_sql(ds=datasource, sql=sanitized_sql, origin_column=False)
    except Exception as e:
        if isinstance(e, ParseSQLResultError):
            raise e
        else:
            err = traceback.format_exc(limit=1, chain=True)
            raise SQLBotDBError(err)


@router.post("/getDataByDbIdAndSqlCsv", dependencies=[Depends(common_headers)])
def get_data_by_db_id_and_sql_csv(current_user: CurrentUser, request: DataSourceRequestWithSql):
    datasource, sanitized_sql = _validate_and_resolve_openapi_sql_query(current_user, request)
    SQLBotLogUtil.info(f"Executing SQL (CSV export) on ds_id {request.db_id}: {request.sql}")
    try:
        result = exec_sql(ds=datasource, sql=sanitized_sql, origin_column=False)
    except Exception as e:
        if isinstance(e, ParseSQLResultError):
            raise e
        else:
            err = traceback.format_exc(limit=1, chain=True)
            raise SQLBotDBError(err)
    fields = result.get("fields") or []
    data = result.get("data") or []
    csv_bytes = _sql_result_to_csv_bytes(fields, data)
    digest = hashlib.sha256(sanitized_sql.encode("utf-8")).hexdigest()[:12]
    filename = f"sql_export_{request.db_id}_{digest}.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/createRecordAndBindDb")
async def bind_data_source(session: SessionDep, current_user: CurrentUser, db_bind_chat: DbBindChat):
    """
    绑定数据源并开始聊天

    根据指定的数据源ID和用户输入，创建一个新的聊天记录并开始聊天。

    Args:
        session: 数据库会话依赖
        current_user: 当前认证用户信息
        db_bind_chat: 包含数据源ID和用户输入的请求对象

    Returns:
        创建的聊天记录对象

    Raises:
        HTTPException: 当处理过程中出现异常时抛出500错误
    """
    try:
        create_chat_obj = CreateChat(
            datasource=db_bind_chat.db_id,
            question=db_bind_chat.title
        )
        return create_chat(session, current_user, create_chat_obj)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/deep-analysis/sessions", response_model=list[Chat], summary="深度分析会话列表",
            description="仅返回 origin=1 的深度分析会话，供深度分析页左侧列表使用",
            dependencies=[Depends(common_headers)])
async def deep_analysis_sessions(session: SessionDep, current_user: CurrentUser):
    return list_deep_analysis_chats(session, current_user)


@router.get(
    "/deep-analysis/workspace-file",
    summary="下载深度分析工作区文件（受控路径）",
    description="仅允许下载当前用户 SQLBOT_HOME 工作区内文件；rel_path 为相对于该用户目录的相对路径（如 exports/a.csv）。",
    dependencies=[Depends(common_headers)],
)
async def deep_analysis_workspace_file(
    session: SessionDep,
    current_user: CurrentUser,
    chat_id: int = Query(..., ge=1, description="深度分析会话 ID，用于校验归属"),
    rel_path: str = Query(..., max_length=2048, description="相对用户工作区根的路径"),
):
    from apps.openapi.agent import sqlbot_workspace as sw

    chat = session.get(Chat, chat_id)
    if (
        chat is None
        or chat.create_by != current_user.id
        or int(chat.origin or 0) != 1
    ):
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    uid = sw.workspace_uid(current_user)
    base = sw.user_dir(uid).resolve()
    rel = (rel_path or "").strip().replace("\\", "/").lstrip("/")
    if not rel or ".." in rel.split("/"):
        raise HTTPException(status_code=400, detail="非法路径")
    target = (base / rel).resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="路径越界")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    suffix = target.suffix.lower()
    media = "application/octet-stream"
    if suffix == ".csv":
        media = "text/csv; charset=utf-8"
    elif suffix in (".html", ".htm"):
        media = "text/html; charset=utf-8"
    elif suffix == ".json":
        media = "application/json; charset=utf-8"
    return FileResponse(target, filename=target.name, media_type=media)


@router.get(
    "/deep-analysis/session-report-html",
    summary="获取深度分析 HTML 报告（动态生成）",
    description="根据会话最新一条带 analysis 的记录生成 HTML（Markdown + 证据表 + 图表）。",
    dependencies=[Depends(common_headers)],
    response_class=HTMLResponse,
)
async def deep_analysis_session_report_html(
    session: SessionDep,
    current_user: CurrentUser,
    chat_id: int = Query(..., ge=1),
):
    from apps.openapi.agent.data_agent_report_html import build_report_html

    chat = session.get(Chat, chat_id)
    if (
        chat is None
        or chat.create_by != current_user.id
        or int(chat.origin or 0) != 1
    ):
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    stmt = (
        select(ChatRecord)
        .where(ChatRecord.chat_id == chat_id)
        .order_by(desc(ChatRecord.create_time))
        .limit(30)
    )
    records = session.exec(stmt).all()
    picked = None
    for rec in records:
        if not rec.analysis:
            continue
        try:
            data = orjson.loads(rec.analysis)
        except Exception:
            continue
        if isinstance(data, dict) and (data.get("report") or "").strip():
            picked = data
            break
    if not picked:
        raise HTTPException(status_code=404, detail="暂无可用的分析报告")
    report_md = picked.get("report") or ""
    evidence = picked.get("evidence")
    if evidence is None:
        evidence = (picked.get("config") or {}).get("evidence")
    if not isinstance(evidence, list):
        evidence = []
    html_doc = build_report_html(report_md, evidence, chat_id=chat_id)
    return HTMLResponse(content=html_doc)


@router.post(
    "/deep-analysis/sessions/batch-delete",
    summary="批量删除深度分析会话",
    description="仅删除当前用户、origin=1 的深度分析会话；无权或不存在 ID 会出现在 skipped_ids",
    dependencies=[Depends(common_headers)],
)
async def deep_analysis_sessions_batch_delete(
    session: SessionDep,
    current_user: CurrentUser,
    body: DeepAnalysisBatchDeleteRequest,
):
    try:
        return delete_deep_analysis_chats_batch(
            session, current_user, list(body.chat_ids)
        )
    except Exception as e:
        SQLBotLogUtil.error(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/deep-analysis/sessions/clean",
    summary="清理深度分析会话历史",
    description="仅清理当前用户 origin=1 的深度分析会话；支持按时间段或全部，与智能问数清空历史语义一致。",
    dependencies=[Depends(common_headers)],
)
async def deep_analysis_sessions_clean(
    session: SessionDep,
    current_user: CurrentUser,
    clean: OpenClean,
):
    try:
        chat_list = _get_deep_analysis_chats_to_clean(session, current_user, clean)
        if not chat_list:
            return _create_clean_response(0, 0, 0)
        success_count, failed_count, _failed = _execute_cleanup(session, chat_list)
        return _create_clean_response(success_count, failed_count, len(chat_list))
    except Exception as e:
        SQLBotLogUtil.error(f"清理深度分析会话异常: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deep-analysis/recommend-questions", summary="深度分析推荐问题（LLM+库表）",
            description="根据所选数据源的表结构，用 LLM 生成 3～5 个适合深度分析的分析目标，用于「试试这些分析目标」",
            dependencies=[Depends(common_headers)])
async def deep_analysis_recommend_questions(
        session: SessionDep,
        current_user: CurrentUser,
        current_assistant: CurrentAssistant,
        datasource_id: int = Query(..., description="数据源 ID"),
):
    """结合库表 schema 用 LLM 推荐深度分析目标，返回 questions 数组。"""
    try:
        oid = current_user.oid if current_user.oid is not None else 1
        ds = session.get(CoreDatasource, datasource_id)
        if not ds or ds.oid != oid:
            raise HTTPException(status_code=404, detail="Datasource not found or no permission")
        schema = get_table_schema(
            session=session,
            current_user=current_user,
            ds=ds,
            question="",
            embedding=False,
        )
        if not (schema and schema.strip()):
            return {"questions": []}
        lang = get_lang_name(getattr(current_user, "language", None) or "")
        tpl = get_base_template()["template"]["deep_analysis_guess"]
        system = tpl["system"].format(lang=lang)
        user = tpl["user"].format(schema=schema)
        messages = [SystemMessage(content=system), HumanMessage(content=user)]
        llm = await create_llm()

        def _invoke():
            return llm.invoke(messages)

        response = await asyncio.to_thread(_invoke)
        content = (response.content or "").strip()
        questions = []
        if content:
            try:
                raw = json.loads(content)
                if isinstance(raw, list):
                    questions = [str(x).strip() for x in raw if x]
                else:
                    questions = []
            except (json.JSONDecodeError, TypeError):
                pass
        return {"questions": questions[:10]}
    except HTTPException:
        raise
    except Exception as e:
        SQLBotLogUtil.error(e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deep-analysis", summary="深度分析",
            description="独立菜单「深度分析」：Agent 自主规划、多次查数、意图驱动分析，流式返回过程与结果",
            dependencies=[Depends(common_headers)])
async def deep_analysis(
        session: SessionDep,
        current_user: CurrentUser,
        body: DeepAnalysisRequest,
        current_assistant: CurrentAssistant
):
    """
    深度分析：根据用户意图自主规划，可多次查数、多次分析，流式返回每步过程与最终结果。
    前端可展示：规划步骤、取数 SQL、执行结果、分析结论、最终报告等。
    """
    try:
        chat_id = body.chat_id
        if chat_id is None:
            create_chat_obj = CreateChat(
                datasource=body.datasource_id,
                question=body.question[:50] if len(body.question) > 50 else body.question,
                origin=1,
            )
            has_ds = body.datasource_id is not None
            chat_info = create_chat(session, current_user, create_chat_obj, require_datasource=has_ds,
                                    current_assistant=current_assistant)
            chat_id = chat_info.id
            if not chat_id:
                raise HTTPException(status_code=500, detail="创建会话失败")

        chat_question = OpenChatQuestion(
            chat_id=chat_id,
            question=body.question,
            task_type="chat",
            chat_mode="plan",
            no_reasoning=body.no_reasoning or False,
            history_open=False,
            max_data_length=body.max_data_length or 1000,
            is_chart_output=body.is_chart_output is not False,
        )

        queue = asyncio.Queue()
        # 立即下发 chat_id，前端可马上插表展示，避免“更新了找不到输出”
        await queue.put({"type": "start", "chat_id": chat_id})
        llm = await create_llm()

        async def _stream(q):
            try:
                while True:
                    try:
                        data = await asyncio.wait_for(q.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    yield 'data:' + orjson.dumps(data).decode() + '\n\n'
                    if isinstance(data, dict) and data.get('type') == 'finish':
                        break
                    if isinstance(data, dict) and data.get('type') == 'error':
                        break
                    if isinstance(data, dict) and data.get('type') == 'start':
                        continue
            except GeneratorExit:
                return
            except Exception as e:
                yield 'data:' + orjson.dumps({
                    'type': 'error',
                    'content': str(e),
                    'reasoning_content': '',
                }).decode() + '\n\n'

        class DeepAnalysisAccumulator:
            """包装 queue，在流式输出时累积 plan/report/process，在 finish 时写入 DB 以便刷新/切回后恢复。"""
            __slots__ = ('_q', '_sess', '_uid', '_cid', '_qtext', '_config', 'plan', 'report', 'process', '_loop', '_report_meta')

            def __init__(self, q, sess, uid, cid, qtext, config=None):
                self._q = q
                self._sess = sess
                self._uid = uid
                self._cid = cid
                self._qtext = qtext or ''
                self._config = config or {}
                self.plan = None
                self.report = None
                self.process = []
                self._loop = None
                self._report_meta = {}

            async def put(self, msg):
                if self._loop is None:
                    self._loop = asyncio.get_running_loop()
                if isinstance(msg, dict):
                    t = msg.get('type')
                    c = msg.get('content')
                    r = msg.get('reasoning_content')
                    if t == 'plan':
                        self.plan = c
                    elif t == 'report':
                        self.report = c
                        rm = {}
                        if 'evidence' in msg:
                            rm['evidence'] = msg['evidence']
                        if msg.get('report_html_relpath'):
                            rm['report_html_relpath'] = msg['report_html_relpath']
                        self._report_meta = rm
                    elif t in (
                        'process',
                        'analysis-result',
                        'chart',
                        'chart-data',
                        'data-finish',
                        'stage',
                    ) or (c or r):
                        entry: dict = {
                            'content': c,
                            'reasoning_content': r,
                            'type': t,
                        }
                        if msg.get('duration_ms') is not None:
                            entry['duration_ms'] = msg['duration_ms']
                        if msg.get('tool'):
                            entry['tool'] = msg['tool']
                        if msg.get('stage') is not None:
                            entry['stage'] = msg['stage']
                        if msg.get('result_summary'):
                            entry['result_summary'] = msg['result_summary']
                        if msg.get('todos') is not None:
                            entry['todos'] = msg['todos']
                        self.process.append(entry)
                    if t == 'finish':
                        from apps.chat.curd.chat import save_deep_analysis_result
                        merged_cfg = dict(self._config)
                        merged_cfg.update(getattr(self, '_report_meta', {}))
                        save_deep_analysis_result(
                            self._sess, self._cid, self._uid, self._qtext,
                            self.plan, self.report, self.process,
                            config=merged_cfg,
                        )
                await self._q.put(msg)

            def put_nowait(self, msg):
                """供同步 Tool 调用：将 put 调度到事件循环并等待完成，与 asyncio.Queue.put_nowait 行为兼容。"""
                if self._loop is None:
                    return
                fut = asyncio.run_coroutine_threadsafe(self.put(msg), self._loop)
                try:
                    fut.result(timeout=10)
                except Exception:
                    pass

        def run_plan(context, user, question, assistant, q):
            from common.core.db import get_db_session
            config = {
                "max_data_length": getattr(body, "max_data_length", None),
                "max_steps": getattr(body, "max_steps", None),
            }
            with get_db_session() as thread_session:
                acc = DeepAnalysisAccumulator(
                    q, thread_session, user.id, question.chat_id, question.question, config=config,
                )
                use_data_agent = getattr(settings, "DATA_AGENT_ENABLED", False)
                use_langgraph = getattr(settings, "DEEP_ANALYSIS_USE_LANGGRAPH", True)

                if use_data_agent:
                    runner = DataAgentRunner(
                        session=thread_session,
                        current_user=user,
                        chat_question=question,
                        queue=acc,
                        max_steps=body.max_steps,
                    )
                    context.run(lambda: asyncio.run(runner.run()))
                elif use_langgraph:
                    runner = DeepAnalysisGraphRunner(
                        session=thread_session,
                        current_user=user,
                        chat_question=question,
                        current_assistant=assistant,
                        queue=acc,
                        max_steps=body.max_steps,
                    )
                    context.run(lambda: asyncio.run(runner.run()))
                else:
                    context.run(lambda: asyncio.run(
                        PlanAgent(
                            session=thread_session,
                            current_user=user,
                            chat_question=question,
                            current_assistant=assistant,
                            max_steps=body.max_steps,
                            queue=acc,
                            llm=llm,
                        ).execute_plan()
                    ))

        thread = threading.Thread(
            target=run_plan,
            args=(contextvars.copy_context(), current_user, chat_question, current_assistant, queue),
            daemon=True,
        )
        thread.start()

        return StreamingResponse(_stream(queue), media_type="text/event-stream")
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/getRecommend", dependencies=[Depends(common_headers)])
async def get_recommend(
        session: SessionDep,
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant
):
    """
    流式生成推荐问题

    基于指定的聊天记录，异步生成推荐问题并以流式方式返回结果。

    Args:
        session: 数据库连接
        current_user: 当前认证用户信息
        chat_record: 聊天对象，包含聊天记录ID
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应，包含生成的推荐问题

    Raises:
        HTTPException: 当聊天记录不存在或处理异常时抛出相应错误
    """
    try:
        chat_record_id = chat_record.chat_record_id
        # 获取聊天记录
        record = None
        for session in get_session():
            record = get_chat_record_by_id(session, chat_record_id)
        # 验证聊天记录是否存在
        if record is None:
            raise HTTPException(
                status_code=400,
                detail=f"Chat record with id {chat_record_id} not found"
            )

        # 创建问题请求对象
        chat_question = OpenChatQuestion(
            chat_id=record.chat_id,
            question=record.question if record.question else ''
        )

        # 创建LLM服务实例并设置推荐问题模式
        llm_service = await LLMService.create(
            session=session,
            current_user=current_user,
            chat_question=chat_question,
            current_assistant=current_assistant,
            no_reasoning=chat_record.no_reasoning,
            embedding=True
        )

        # 设置聊天记录
        llm_service.set_record(record)

        # 异步运行推荐问题生成任务
        llm_service.run_recommend_questions_task_async()
    except Exception as e:
        # 打印异常堆栈信息用于调试
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # 返回流式响应
    return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")


@router.post("/deleteChats", summary="清理智能问数",
             description="仅清理智能问数会话（不包含深度分析）。支持：按会话ID、按时间段、清空全部。",
             dependencies=[Depends(common_headers)])
async def clean_all_chat_record(
        session: SessionDep,
        current_user: CurrentUser,
        clean: OpenClean
):
    """
    清理当前用户的智能问数聊天记录（不清理深度分析 origin=1）。

    Args:
        session: 数据库会话依赖
        current_user: 当前认证用户信息
        clean: 清理对象（chat_ids / start_time+end_time / 空为清空全部智能问数）

    Returns:
        dict: 操作结果，包含成功和失败的记录数
    """
    try:
        # 获取要清理的聊天记录列表
        chat_list = _get_chats_to_clean(session, current_user, clean)

        if not chat_list:
            return _create_clean_response(0, 0, 0)

        # 执行清理操作
        success_count, failed_count, failed_records = _execute_cleanup(
            session,
            chat_list
        )

        # 返回操作结果
        return _create_clean_response(success_count, failed_count, len(chat_list))

    except Exception as e:
        SQLBotLogUtil.error(f"清理聊天记录异常: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"清理聊天记录失败: {str(e)}"
        )


@router.post("/analysis", summary="分析",
             description="对指定聊天记录进行分析",
             dependencies=[Depends(common_headers)])
async def analysis_chat_record(
        session: SessionDep,
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant
):
    """
    对指定聊天记录进行分析

    Args:
        session: 数据库连接
        current_user: 当前认证用户信息
        chat_record: 聊天对象，包含聊天记录ID
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应，包含分析结果
    """
    return await _run_analysis_or_predict(session, current_user, chat_record, current_assistant, 'analysis')


@router.post("/predict", summary="预测",
             description="对指定聊天记录进行预测",
             dependencies=[Depends(common_headers)])
async def predict_chat_record(
        session: SessionDep,
        current_user: CurrentUser,
        chat_record: OpenChat,
        current_assistant: CurrentAssistant
):
    """
    对指定聊天记录进行预测

    Args:
        session: 数据库连接
        current_user: 当前认证用户信息
        chat_record: 聊天对象，包含聊天记录ID
        current_assistant: 当前使用的AI助手信息

    Returns:
        StreamingResponse: 流式响应，包含预测结果
    """
    return await _run_analysis_or_predict(session, current_user, chat_record, current_assistant, 'predict')


@router.post("/uploadExcelAndCreateDatasource", response_model=CoreDatasource)
async def upload_excel_and_create_datasource(
        session: SessionDep,
        trans: Trans,
        user: CurrentUser,
        file: UploadFile = File(...),
        example_size: int = Form(10),
        ai: bool = Form(False),
):
    extensions = {"xlsx", "xls", "csv"}
    if not file.filename.lower().endswith(tuple(extensions)):
        raise HTTPException(400, "Only support .xlsx/.xls/.csv")

    os.makedirs(path, exist_ok=True)
    filename = f"{file.filename.split('.')[0]}_{hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:10]}.{file.filename.split('.')[1]}"
    save_path = os.path.join(path, filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())

    def inner():
        try:
            return upload_excel_and_create_datasource_service(
                session, trans, user, save_path, filename,
                example_size, ai
            )
        finally:
            SQLBotLogUtil.info("上传结束")

    return await asyncio.to_thread(inner)


@router.post("/addPg", response_model=CoreDatasource)
async def add(session: SessionDep, trans: Trans, user: CurrentUser, config: SinglePgConfig):
    conf_dict = DatasourceConf(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password,
        database=config.database,
        driver=config.driver,
        extraJdbc=config.extraJdbc,
        dbSchema=config.dbSchema,
        filename=config.filename,
        sheets=config.sheets,
        mode=config.mode,
        timeout=config.timeout
    )
    # 将模型转换为字典以便JSON序列化
    conf_dict_as_dict = conf_dict.dict() if hasattr(conf_dict, 'dict') else vars(conf_dict)
    configuration_encrypted = aes_encrypt(json.dumps(conf_dict_as_dict, ensure_ascii=False))

    tables_payload = [CoreTable(table_name=config.tableName, table_comment=config.tableComment)]

    db = CreateDatasource(
        name=config.tableComment,
        type="pg",
        configuration=configuration_encrypted,
        tables=tables_payload,
    )

    def inner():
        return create_ds(session, trans, user, db)

    return await asyncio.to_thread(inner)


@router.post(
    "/deleteDatasource",
    summary="根据 ID 删除数据源",
    description="删除指定数据源及其关联的表、字段记录。",
    dependencies=[Depends(common_headers)],
)
async def delete_datasource_by_id(session: SessionDep, id: int):
    """
    删除数据源：
    - 对 Excel 类型，自动 DROP 物理表；
    - 清理 CoreTable/CoreField 记录；
    - 日志可追溯。
    """

    def inner():
        return delete_ds(session, id)

    return await asyncio.to_thread(inner)


@router.post(
    "/deleteExcels",
    summary="清空excel",
    description="清空excel",
    dependencies=[Depends(common_headers)],
)
async def delete_excels(session: SessionDep, user: CurrentUser):
    """
    删除数据源：
    - 对 Excel 类型，自动 DROP 物理表；
    - 清理 CoreTable/CoreField 记录；
    - 日志可追溯。
    """

    def inner():
        ids: list[int] = get_datasource_list_for_openapi_excels(session, user)
        for id in ids:
            delete_ds(session, id)

    return await asyncio.to_thread(inner)
