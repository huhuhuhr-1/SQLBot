# import asyncio
# import hashlib
# import json
# import os
# import uuid
# from typing import List
#
# from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
#
# from apps.datasource.crud.datasource import get_datasource_list_for_openapi, get_datasource_list_for_openapi_excels, \
#     create_ds
# from apps.datasource.models.datasource import CoreDatasource, CreateDatasource, CoreTable, DatasourceConf
# from apps.datasource.utils.utils import aes_encrypt
# from apps.openapi.dao.openapiDao import get_datasource_by_name_or_id
# from apps.openapi.models.openapiModels import DataSourceRequest, SinglePgConfig, common_headers
# from apps.openapi.service.openapi_db import delete_ds, upload_excel_and_create_datasource_service
# from common.core.config import settings
# from common.core.deps import SessionDep, CurrentUser, Trans
#
# router = APIRouter(tags=["datasource"])
# path = settings.EXCEL_PATH
#
#
# @router.get("/getDataSourceList", summary="获取数据源列表",
#             description="获取当前用户可访问的数据源列表",
#             dependencies=[Depends(common_headers)])
# async def get_data_source_list(session: SessionDep, user: CurrentUser):
#     """
#     获取数据源列表
#
#     获取当前认证用户可访问的所有数据源列表。
#
#     Args:
#         session: 数据库会话依赖
#         user: 当前认证用户信息
#
#     Returns:
#         用户可访问的数据源列表
#     """
#     return get_datasource_list_for_openapi(session=session, user=user)
#
#
# @router.post("/getDataSourceByIdOrName", summary="根据ID或名称获取数据源",
#              description="根据数据源ID或名称获取特定数据源信息",
#              dependencies=[Depends(common_headers)])
# async def get_data_source_by_id_or_name(
#         session: SessionDep,
#         user: CurrentUser,
#         request: DataSourceRequest
# ):
#     """
#     根据ID或名称获取数据源
#
#     根据数据源ID或名称获取特定数据源信息。
#
#     Args:
#         session: 数据库会话依赖
#         user: 当前认证用户信息
#         request: 数据源查询请求
#
#     Returns:
#         数据源信息
#     """
#     return get_datasource_by_name_or_id(session=session, user=user, query=request)
#
#
# @router.post("/uploadExcelAndCreateDatasource", response_model=CoreDatasource)
# async def upload_excel_and_create_datasource(
#         session: SessionDep,
#         trans: Trans,
#         user: CurrentUser,
#         file: UploadFile = File(...),
#         example_size: int = Form(10),
#         ai: bool = Form(False),
# ):
#     """
#     上传Excel文件并创建数据源
#
#     Args:
#         session: 数据库会话依赖
#         trans: 国际化翻译依赖
#         user: 当前认证用户信息
#         file: 上传的Excel文件
#         example_size: 示例数据大小
#         ai: 是否使用AI处理
#
#     Returns:
#         CoreDatasource: 创建的数据源信息
#
#     Raises:
#         HTTPException: 当文件格式不支持时抛出400错误
#     """
#     extensions = {"xlsx", "xls", "csv"}
#     if not file.filename.lower().endswith(tuple(extensions)):
#         raise HTTPException(400, "Only support .xlsx/.xls/.csv")
#
#     os.makedirs(path, exist_ok=True)
#     filename = f"{file.filename.split('.')[0]}_{hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:10]}.{file.filename.split('.')[1]}"
#     save_path = os.path.join(path, filename)
#     with open(save_path, "wb") as f:
#         f.write(await file.read())
#
#     def inner():
#         try:
#             return upload_excel_and_create_datasource_service(
#                 session, trans, user, save_path, filename,
#                 example_size, ai
#             )
#         finally:
#             from common.utils.utils import SQLBotLogUtil
#             SQLBotLogUtil.info("上传结束")
#
#     return await asyncio.to_thread(inner)
#
#
# @router.post("/addPg", response_model=CoreDatasource)
# async def add(session: SessionDep, trans: Trans, user: CurrentUser, config: SinglePgConfig):
#     """
#     添加PostgreSQL数据源
#
#     Args:
#         session: 数据库会话依赖
#         trans: 国际化翻译依赖
#         user: 当前认证用户信息
#         config: PostgreSQL配置信息
#
#     Returns:
#         CoreDatasource: 创建的数据源信息
#     """
#     conf_dict = DatasourceConf(
#         host=config.host,
#         port=config.port,
#         username=config.username,
#         password=config.password,
#         database=config.database,
#         driver=config.driver,
#         extraJdbc=config.extraJdbc,
#         dbSchema=config.dbSchema,
#         filename=config.filename,
#         sheets=config.sheets,
#         mode=config.mode,
#         timeout=config.timeout
#     )
#     # 将模型转换为字典以便JSON序列化
#     conf_dict_as_dict = conf_dict.dict() if hasattr(conf_dict, 'dict') else vars(conf_dict)
#     configuration_encrypted = aes_encrypt(json.dumps(conf_dict_as_dict, ensure_ascii=False))
#
#     tables_payload = [CoreTable(table_name=config.tableName, table_comment=config.tableComment)]
#
#     db = CreateDatasource(
#         name=config.tableComment,
#         type="pg",
#         configuration=configuration_encrypted,
#         tables=tables_payload,
#     )
#
#     def inner():
#         return create_ds(session, trans, user, db)
#
#     return await asyncio.to_thread(inner)
#
#
# @router.post(
#     "/deleteDatasource",
#     summary="根据 ID 删除数据源",
#     description="删除指定数据源及其关联的表、字段记录。",
#     dependencies=[Depends(common_headers)],
# )
# async def delete_datasource_by_id(session: SessionDep, id: int):
#     """
#     删除数据源：
#     - 对 Excel 类型，自动 DROP 物理表；
#     - 清理 CoreTable/CoreField 记录；
#     - 日志可追溯。
#
#     Args:
#         session: 数据库会话依赖
#         id: 数据源ID
#
#     Returns:
#         删除操作结果
#     """
#
#     def inner():
#         return delete_ds(session, id)
#
#     return await asyncio.to_thread(inner)
#
#
# @router.post(
#     "/deleteExcels",
#     summary="清空excel",
#     description="清空excel",
#     dependencies=[Depends(common_headers)],
# )
# async def delete_excels(session: SessionDep, user: CurrentUser):
#     """
#     删除Excel数据源：
#     - 对 Excel 类型，自动 DROP 物理表；
#     - 清理 CoreTable/CoreField 记录；
#     - 日志可追溯。
#
#     Args:
#         session: 数据库会话依赖
#         user: 当前认证用户信息
#
#     Returns:
#         删除操作结果
#     """
#
#     def inner():
#         ids: List[int] = get_datasource_list_for_openapi_excels(session, user)
#         for id in ids:
#             delete_ds(session, id)
#
#     return await asyncio.to_thread(inner)