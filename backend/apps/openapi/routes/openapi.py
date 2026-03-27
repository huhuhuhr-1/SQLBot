# from fastapi import APIRouter
#
# # 导入各个子路由模块
# from apps.openapi.routes.auth_routes import router as auth_router
# from apps.openapi.routes.chat_routes import router as chat_router
# from apps.openapi.routes.datasource_routes import router as datasource_router
# from apps.openapi.routes.data_routes import router as data_router
#
# # 创建主路由器
# router = APIRouter(tags=["openapi"], prefix="/openapi")
#
# # 注册子路由，保持原有的API路径
# router.include_router(auth_router, prefix="/auth")
# router.include_router(chat_router, prefix="/chat")
# router.include_router(datasource_router, prefix="/datasource")
# router.include_router(data_router, prefix="/data")
