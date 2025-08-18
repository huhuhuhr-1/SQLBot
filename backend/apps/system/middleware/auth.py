"""认证中间件，校验用户和助手的访问令牌。"""

from typing import Optional
from fastapi import Request
from fastapi.responses import JSONResponse
import jwt
from sqlmodel import Session
from starlette.middleware.base import BaseHTTPMiddleware
from apps.system.models.system_model import AssistantModel
from common.core.db import engine 
from apps.system.crud.assistant import get_assistant_info, get_assistant_user
from apps.system.crud.user import get_user_info
from apps.system.schemas.system_schema import AssistantHeader, UserInfoDTO
from common.core import security
from common.core.config import settings
from common.core.schemas import TokenPayload
from common.utils.locale import I18n
from common.utils.utils import SQLBotLogUtil
from common.utils.whitelist import whiteUtils
from fastapi.security.utils import get_authorization_scheme_param
from common.core.deps import get_i18n


class TokenMiddleware(BaseHTTPMiddleware):
    """从请求头验证 Token 的中间件。"""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request, call_next):
        """处理每个请求的认证逻辑。"""

        # 跳过预检或白名单路径
        if self.is_options(request) or whiteUtils.is_whitelisted(request.url.path):
            return await call_next(request)
        assistantTokenKey = settings.ASSISTANT_TOKEN_KEY
        assistantToken = request.headers.get(assistantTokenKey)
        trans = await get_i18n(request)
        # 如果携带了助手 Token，先进行助手校验
        if assistantToken:
            validator: tuple[any] = await self.validateAssistant(assistantToken)
            if validator[0]:
                request.state.current_user = validator[1]
                request.state.assistant = validator[2]
                return await call_next(request)
            message = trans('i18n_permission.authenticate_invalid', msg = validator[1])
            return JSONResponse(message, status_code=401, headers={"Access-Control-Allow-Origin": "*"})
        # 校验用户 Token
        tokenkey = settings.TOKEN_KEY
        token = request.headers.get(tokenkey)
        validate_pass, data = await self.validateToken(token, trans)
        if validate_pass:
            request.state.current_user = data
            return await call_next(request)

        message = trans('i18n_permission.authenticate_invalid', msg = data)
        return JSONResponse(message, status_code=401, headers={"Access-Control-Allow-Origin": "*"})

    def is_options(self, request: Request):
        """判断是否为预检请求。"""
        return request.method == "OPTIONS"

    async def validateToken(self, token: Optional[str], trans: I18n):
        """校验用户 Token 并返回用户信息。"""
        if not token:
            return False, f"Miss Token[{settings.TOKEN_KEY}]!"
        schema, param = get_authorization_scheme_param(token)
        if schema.lower() != "bearer":
            return False, f"Token schema error!"
        try:
            payload = jwt.decode(
                param, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
            )
            token_data = TokenPayload(**payload)
            with Session(engine) as session:
                session_user = await get_user_info(session = session, user_id = token_data.id)
                if not session_user:
                    message = trans('i18n_not_exist', msg = trans('i18n_user.account'))
                    raise Exception(message)
                session_user = UserInfoDTO.model_validate(session_user)
                if session_user.status != 1:
                    message = trans('i18n_login.user_disable', msg = trans('i18n_concat_admin'))
                    raise Exception(message)
                if not session_user.oid or session_user.oid == 0:
                    message = trans('i18n_login.no_associated_ws', msg = trans('i18n_concat_admin'))
                    raise Exception(message)
                return True, session_user
        except Exception as e:
            msg = str(e)
            SQLBotLogUtil.exception(f"Token validation error: {msg}")
            if 'expired' in msg:
                return False, jwt.ExpiredSignatureError(trans('i18n_permission.token_expired'))
            return False, e

    async def validateAssistant(self, assistantToken: Optional[str]) -> tuple[any]:
        """校验助手 Token 并返回助手及用户信息。"""
        if not assistantToken:
            return False, f"Miss Token[{settings.TOKEN_KEY}]!"
        schema, param = get_authorization_scheme_param(assistantToken)
        if schema.lower() != "assistant":
            return False, f"Token schema error!"

        try:
            payload = jwt.decode(
                param, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
            )
            token_data = TokenPayload(**payload)
            if not payload['assistant_id']:
                return False, f"Miss assistant payload error!"
            with Session(engine) as session:
                """ session_user = await get_user_info(session = session, user_id = token_data.id)
                session_user = UserInfoDTO.model_validate(session_user) """
                session_user = get_assistant_user(id = token_data.id)
                assistant_info = await get_assistant_info(session=session, assistant_id=payload['assistant_id'])
                assistant_info = AssistantModel.model_validate(assistant_info)
                assistant_info = AssistantHeader.model_validate(assistant_info.model_dump(exclude_unset=True))
                return True, session_user, assistant_info
        except Exception as e:
            SQLBotLogUtil.exception(f"Assistant validation error: {str(e)}")
            # Return False and the exception message
            return False, e
