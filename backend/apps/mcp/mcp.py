# Author: Junjun
# Date: 2025/7/1

from datetime import timedelta

import jwt
from fastapi import HTTPException, status, APIRouter
from fastapi.responses import StreamingResponse
# from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import select

from apps.chat.api.chat import create_chat
from apps.chat.models.chat_model import ChatMcp, CreateChat, ChatStart, McpQuestion
from apps.chat.task.llm import LLMService
from apps.system.crud.user import authenticate
from apps.system.crud.user import get_db_user
from apps.system.models.system_model import UserWsModel
from apps.system.models.user import UserModel
from apps.system.schemas.system_schema import BaseUserDTO
from apps.system.schemas.system_schema import UserInfoDTO
from common.core import security
from common.core.config import settings
from common.core.deps import SessionDep
from common.core.schemas import TokenPayload, XOAuth2PasswordBearer, Token
from common.core.security import create_access_token

reusable_oauth2 = XOAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

router = APIRouter(tags=["mcp"], prefix="/mcp")


# @router.post("/access_token", operation_id="access_token")
# def local_login(
#         session: SessionDep,
#         form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
# ) -> Token:
#     user = authenticate(session=session, account=form_data.username, password=form_data.password)
#     if not user:
#         raise HTTPException(status_code=400, detail="Incorrect account or password")
#     access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#     user_dict = user.to_dict()
#     return Token(access_token=create_access_token(
#         user_dict, expires_delta=access_token_expires
#     ))


# @router.get("/ds_list", operation_id="get_datasource_list")
# async def datasource_list(session: SessionDep):
#     return get_datasource_list(session=session)
#
#
# @router.get("/model_list", operation_id="get_model_list")
# async def get_model_list(session: SessionDep):
#     return session.query(AiModelDetail).all()


@router.post("/mcp_start", operation_id="mcp_start")
async def mcp_start(session: SessionDep, chat: ChatStart):
    user: BaseUserDTO = authenticate(session=session, account=chat.username, password=chat.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect account or password")

    if not user.oid or user.oid == 0:
        raise HTTPException(status_code=400, detail="No associated workspace, Please contact the administrator")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_dict = user.to_dict()
    t = Token(access_token=create_access_token(
        user_dict, expires_delta=access_token_expires
    ))
    c = create_chat(session, user, CreateChat(origin=1), False)
    return {"access_token": t.access_token, "chat_id": c.id}


@router.post("/mcp_question", operation_id="mcp_question")
async def mcp_question(session: SessionDep, chat: McpQuestion):
    try:
        payload = jwt.decode(
            chat.token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    # session_user = await get_user_info(session=session, user_id=token_data.id)

    db_user: UserModel = get_db_user(session=session, user_id=token_data.id)
    session_user = UserInfoDTO.model_validate(db_user.model_dump())
    session_user.isAdmin = session_user.id == 1 and session_user.account == 'admin'
    if session_user.isAdmin:
        session_user = session_user
    ws_model: UserWsModel = session.exec(
        select(UserWsModel).where(UserWsModel.uid == session_user.id, UserWsModel.oid == session_user.oid)).first()
    session_user.weight = ws_model.weight if ws_model else -1

    session_user = UserInfoDTO.model_validate(session_user)
    if not session_user:
        raise HTTPException(status_code=404, detail="User not found")

    if session_user.status != 1:
        raise HTTPException(status_code=400, detail="Inactive user")

    mcp_chat = ChatMcp(token=chat.token, chat_id=chat.chat_id, question=chat.question)
    # ask
    llm_service = await LLMService.create(session_user, mcp_chat)
    llm_service.init_record()

    return StreamingResponse(llm_service.run_task(False), media_type="text/event-stream")
