import json
import logging
import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from fastapi_mcp import FastApiMCP

from config import settings, Settings
from sqlbot_client import (
    get_sqlbot_client,
    TokenResponse,
    DatabaseListResponse,
    ChatRequest,
    DataSourceDetailResponse,
    DataSourceRequest,
    ChatRecordRequest
)

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 验证必要配置
if not settings.validate_sqlbot_config():
    logger.error("SQLBot 配置不完整，请检查环境变量")
    raise RuntimeError("SQLBot 配置不完整")

app = FastAPI(
    title=settings.app_name,
    description="SQLBot MCP Server for AI Assistant Integration",
    version=settings.app_version
)

mcp = FastApiMCP(app, name="SQLBot MCP Server", description="SQLBot MCP Server")
mcp.mount_http(app)  # MCP server


# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """处理 HTTP 异常"""
    from fastapi.responses import JSONResponse
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "type": "http_error"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """处理未捕获的异常"""
    from fastapi.responses import JSONResponse
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "type": "server_error"
            }
        }
    )


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """健康检查端点"""
    try:
        # 测试 SQLBot 连接
        client = get_sqlbot_client()
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "sqlbot_url": settings.sqlbot_base_url,
            "timestamp": os.getenv("TIMESTAMP", "")
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "error": str(e),
            "timestamp": os.getenv("TIMESTAMP", "")
        }


@app.get("/create_chat", operation_id="create_chat")
async def get_token() -> Dict[str, Any]:
    """
    获取 SQLBot 访问令牌, 获取chat_id和access_token。不需要频繁创建。

    Args:
        create_chat: 创建聊天会话

    Returns:
        Dict[str, Any]: 令牌信息字典

    Raises:
        HTTPException: 获取令牌失败时抛出
    """

    try:
        client = get_sqlbot_client()
        token_response = await client.get_token(create_chat=True)

        # 将 TokenResponse 转换为字典格式，保持与原有 API 兼容
        result = {
            "access_token": token_response.access_token,
            "token_type": token_response.token_type,
            "expire": token_response.expire,
            "chat_id": token_response.chat_id
        }

        logger.info("Successfully retrieved token")
        return result

    except HTTPException:
        # 重新抛出 HTTPException
        raise
    except Exception as e:
        error_msg = f"Error getting token: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/question", operation_id="question")
async def chat_endpoint(
        question: str = Query(..., description="用户问题"),
        chat_id: int = Query(..., description="聊天ID")
):
    """
    SQLBot 通过自然语言问数据 - 流式输出，chat_id请从create_chat中获取，相同chat_id共享上下文。

    Args:
        question: 用户问题
        chat_id: 聊天ID
    Returns:
        StreamingResponse: 流式响应，每行包含一个 JSON 对象

    Raises:
        HTTPException: 聊天请求失败时抛出
    """

    try:
        client = get_sqlbot_client()

        data_source_detail = await client.get_data_source_by_name(settings.db_name)
        db_id: int = data_source_detail.id
        logger.info(f"Received chat request: question='{question}', chat_id={chat_id}, db_id={db_id}")
        # 将 DataSourceDetailResponse 转换为字典格式
        result = data_source_detail.model_dump()

        logger.info(f"Successfully retrieved data source: {data_source_detail.name}")

        async def generate_chat_stream():
            """生成聊天流式响应"""
            try:
                async for chunk in client.chat_stream(question, chat_id, db_id):
                    # 将数据格式化为 SSE 格式
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error(f"Error in chat stream: {str(e)}")
                # 发送错误消息
                error_chunk = {
                    "type": "error",
                    "message": str(e)
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_chat_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )

    except HTTPException:
        # 重新抛出 HTTPException
        raise
    except Exception as e:
        error_msg = f"Error in chat endpoint: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/get_question_data", operation_id="get_question_data")
async def get_question_data(request: ChatRecordRequest):
    """
    获取聊天记录

    Args:
        request: 获取question的数据详情，chat_record_id从question接口返回获取，类型是data-finish,content的值为chat_record_id {"content":21,"type":"data-finish"}.

    Returns:
        Dict[str, Any]: 聊天记录数据

    Raises:
        HTTPException: 获取聊天记录失败时抛出
    """
    logger.info(f"Received request to get chat record: chat_record_id={request.chat_record_id}")

    try:
        client = get_sqlbot_client()
        chat_record_data = await client.get_chat_record(request.chat_record_id)

        logger.info(f"Successfully retrieved chat record: chat_record_id={request.chat_record_id}")
        return chat_record_data

    except HTTPException:
        # 重新抛出 HTTPException
        raise
    except Exception as e:
        error_msg = f"Error getting chat record: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


# But if you re-run the setup, the new endpoints will now be exposed.
mcp.setup_server()

if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"SQLBot URL: {settings.sqlbot_base_url}")
    logger.info(f"Server will start on {settings.host}:{settings.port}")

    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )
