# from typing import Optional
#
# from fastapi import APIRouter, Depends
#
# from apps.chat.curd.chat import create_chat
# from apps.chat.models.chat_model import CreateChat
# from apps.openapi.models.openapiModels import TokenRequest, OpenToken, common_headers
# from apps.openapi.service.openapi_service import create_access_token_with_expiry
# from apps.system.crud.user import authenticate
# from apps.system.schemas.system_schema import BaseUserDTO
# from common.core.deps import SessionDep, Trans
#
# router = APIRouter(tags=["auth"])
#
#
# @router.post("/getToken", summary="创建认证令牌",
#              description="使用用户名和密码创建一个用于API认证的访问令牌")
# async def get_token(
#         session: SessionDep,
#         trans: Trans,
#         request: TokenRequest
# ) -> OpenToken:
#     """
#     创建认证令牌
#
#     使用用户名和密码创建一个用于API认证的访问令牌。
#     此接口遵循标准的认证流程，用于获取后续API调用所需的访问凭证。
#
#     Args:
#         session: 数据库会话依赖
#         trans: 国际化翻译依赖
#         request: 包含用户名和密码的请求体数据
#
#     Returns:
#         OpenToken: 包含访问令牌、过期时间和聊天ID的响应对象
#
#     Raises:
#         HTTPException: 当认证失败、用户无工作空间关联或用户被禁用时抛出400错误
#     """
#     # 验证用户身份
#     user: BaseUserDTO = authenticate(
#         session=session,
#         account=request.username,
#         password=request.password
#     )
#
#     # 验证用户状态
#     from apps.openapi.service.openapi_service import validate_user_status
#     validate_user_status(user, trans)
#
#     # 创建访问令牌和过期时间
#     access_token, expire_time = create_access_token_with_expiry(user.to_dict())
#
#     # 处理聊天会话创建请求
#     chat_id: Optional[int] = None
#     if request.create_chat:
#         record = create_chat(session, user, CreateChat(origin=1), False)
#         chat_id = record.id
#
#     # 创建并返回访问令牌
#     return OpenToken(
#         access_token=f"bearer {access_token}",
#         expire=expire_time,
#         chat_id=chat_id
#     )
