"""SQLBot 后端应用入口。"""

import sqlbot_xpack
from alembic.config import Config
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from fastapi_mcp import FastApiMCP
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from alembic import command
from apps.api import api_router
from apps.system.crud.assistant import init_dynamic_cors
from apps.system.middleware.auth import TokenMiddleware
from common.core.config import settings
from common.core.response_middleware import ResponseMiddleware, exception_handler
from common.core.sqlbot_cache import init_sqlbot_cache
from common.utils.utils import SQLBotLogUtil


def run_migrations():
    """执行数据库迁移，确保在启动时数据库结构保持最新。"""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """在 FastAPI 生命周期中执行初始化和清理逻辑。"""
    # 初始化数据库及缓存
    run_migrations()
    init_sqlbot_cache()
    init_dynamic_cors(app)
    SQLBotLogUtil.info("✅ SQLBot 初始化完成")
    await sqlbot_xpack.core.clean_xpack_cache()
    # 让应用继续运行
    yield
    # 应用关闭时打印日志
    SQLBotLogUtil.info("SQLBot 应用关闭")


def custom_generate_unique_id(route: APIRoute) -> str:
    """根据路由标签和名称生成 Swagger 文档中唯一的 ID。"""
    tag = route.tags[0] if route.tags and len(route.tags) > 0 else ""
    return f"{tag}-{route.name}"


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)

# 独立的 FastAPI 应用，用于 MCP(模型控制协议) 接口
mcp_app = FastAPI()
# 提供 MCP 相关静态资源（如图片）
mcp_app.mount("/images", StaticFiles(directory=settings.MCP_IMAGE_PATH), name="images")

# 封装主应用为 MCP Server，暴露额外的插件能力
mcp = FastApiMCP(
    app,
    name="SQLBot MCP Server",
    description="SQLBot MCP Server",
    describe_all_responses=True,
    describe_full_response_schema=True,
    include_operations=["get_datasource_list", "get_model_list", "mcp_question", "mcp_start"],
)

mcp.mount(mcp_app)

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(TokenMiddleware)
app.add_middleware(ResponseMiddleware)
app.include_router(api_router, prefix=settings.API_V1_STR)

# Register exception handlers
app.add_exception_handler(StarletteHTTPException, exception_handler.http_exception_handler)
app.add_exception_handler(Exception, exception_handler.global_exception_handler)

mcp.setup_server()

sqlbot_xpack.init_fastapi_app(app)
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # uvicorn.run("main:mcp_app", host="0.0.0.0", port=8001) # mcp server
