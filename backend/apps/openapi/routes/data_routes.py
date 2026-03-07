# import asyncio
# import traceback
#
# from fastapi import APIRouter, Depends, HTTPException
#
# from apps.chat.curd.chat import get_chat_chart_data
# from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id
# from apps.openapi.models.openapiModels import OpenChat, DataSourceRequestWithSql, common_headers
# from apps.openapi.service.openapi_service import is_safe_sql
# from common.core.db import get_session
# from common.core.deps import SessionDep, CurrentUser
# from common.error import ParseSQLResultError, SQLBotDBError
# from common.utils.utils import SQLBotLogUtil
#
# router = APIRouter(tags=["data"])
#
#
# @router.post("/getData", dependencies=[Depends(common_headers)])
# async def get_data(session: SessionDep, record_chat: OpenChat):
#     """
#     获取聊天记录数据
#
#     根据聊天记录ID获取相关的图表数据。
#
#     Args:
#         session: 数据库会话依赖
#         record_chat: 聊天对象，包含图表记录ID
#
#     Returns:
#         聊天记录对应的图表数据
#     """
#
#     def _fetch_chart_data() -> dict:
#         """内部函数：执行数据库查询获取图表数据"""
#         return get_chat_chart_data(
#             chat_record_id=record_chat.chat_record_id,
#             session=session
#         )
#
#     # 使用异步线程执行数据库查询
#     return await asyncio.to_thread(_fetch_chart_data)
#
#
# @router.post("/getDataByDbIdAndSql", dependencies=[Depends(common_headers)])
# def get_data_by_db_id_and_sql(current_user: CurrentUser, request: DataSourceRequestWithSql):
#     """
#     根据数据库ID和SQL获取数据
#
#     Args:
#         current_user: 当前认证用户
#         request: 包含数据库ID和SQL查询的请求对象
#
#     Returns:
#         查询结果数据
#
#     Raises:
#         HTTPException: 当参数缺失或SQL不安全时抛出400错误
#         SQLBotDBError: 当数据库操作失败时抛出
#     """
#     # 验证输入参数
#     if not request.db_id:
#         raise HTTPException(
#             status_code=400,
#             detail="db_id 参数不能为空"
#         )
#
#     if not request.sql:
#         raise HTTPException(
#             status_code=400,
#             detail="sql 参数不能为空"
#         )
#
#     # 增加SQL注入防护：检查SQL语句中是否包含危险操作
#     sanitized_sql = request.sql.strip()
#     if not is_safe_sql(sanitized_sql):
#         raise HTTPException(
#             status_code=400,
#             detail="SQL语句包含不安全的操作"
#         )
#
#     datasource = None
#     # 以更标准的方式使用数据库会话
#     for session in get_session():
#         try:
#             datasource = get_datasource_by_name_or_id(
#                 session=session,
#                 user=current_user,
#                 query=DataSourceRequest(id=int(request.db_id))
#             )
#             if datasource is None:
#                 raise HTTPException(
#                     status_code=500,
#                     detail="数据源未找到"
#                 )
#             break
#         finally:
#             # 确保会话被正确关闭
#             session.close()
#
#     SQLBotLogUtil.info(f"Executing SQL on ds_id {request.db_id}: {request.sql}")
#     try:
#         # 使用 datasource 而不是 request.ds
#         from apps.db.db import exec_sql
#         return exec_sql(ds=datasource, sql=sanitized_sql, origin_column=False)
#     except Exception as e:
#         if isinstance(e, ParseSQLResultError):
#             raise e
#         else:
#             err = traceback.format_exc(limit=1, chain=True)
#             raise SQLBotDBError(err)