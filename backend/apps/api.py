from fastapi import APIRouter

from apps.terminology.api import terminology
from apps.chat.api import chat
from apps.dashboard.api import dashboard_api
from apps.datasource.api import datasource
from apps.system.api import login, user, aimodel, workspace, assistant
from apps.mcp import mcp

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(user.router)
api_router.include_router(workspace.router)
api_router.include_router(assistant.router)
api_router.include_router(aimodel.router)
api_router.include_router(terminology.router)
api_router.include_router(datasource.router)
api_router.include_router(chat.router)
api_router.include_router(dashboard_api.router)
api_router.include_router(mcp.router)


