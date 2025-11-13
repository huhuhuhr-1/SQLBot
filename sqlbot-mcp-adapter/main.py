import logging

import httpx
from fastapi import FastAPI, HTTPException
from fastapi_mcp import FastApiMCP

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

mcp = FastApiMCP(app, name="SQLBot MCP Server", description="SQLBot MCP Server")
mcp.mount_http(app)  # MCP server


def get_token(create_chat: bool = True):
    """
    获取 SQLBot 访问令牌
    """
    logger.info(f"Received request to get token, create_chat={create_chat}")

    # 从环境变量获取配置
    sqlbot_base_url = os.getenv("SQLBOT_BASE_URL", "http://localhost:8000/api/v1")
    username = os.getenv("SQLBOT_USERNAME", "admin")
    password = os.getenv("SQLBOT_PASSWORD", "SQLBot@123456")

    logger.info(f"Attempting to get token from {sqlbot_base_url} for user {username}")

    if not username or not password:
        error_msg = "SQLBot username or password not configured"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        request_data = {
            "username": username,
            "password": password,
            "create_chat": create_chat
        }
        logger.debug(f"Sending request to {sqlbot_base_url}/openapi/getToken with data: {request_data}")

        response = httpx.post(
            f"{sqlbot_base_url}/openapi/getToken",
            json=request_data
        )

        logger.info(f"Response status: {response.status_code}")
        if response.status_code != 200:
            error_msg = f"Failed to get token: {response.text}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        result = response.json()
        logger.debug(f"Response data: {result}")

        if result.get("code") != 0:
            error_msg = f"Token request failed: {result.get('msg', 'Unknown error')}"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        logger.info("Successfully retrieved token")
        return result.get("data", {})
    except httpx.RequestError as e:
        error_msg = f"Request error: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
    except Exception as e:
        error_msg = f"Error getting token: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/get_database_list", operation_id="get_database_list")
async def get_database_list():
    """
    获取数据源列表 - 无需任何参数
    """
    logger.info(f"Received request to get database list with token header")

    # 从环境变量获取配置
    sqlbot_base_url = os.getenv("SQLBOT_BASE_URL", "http://localhost:8000/api/v1")

    logger.info(f"Attempting to get database list from {sqlbot_base_url}")

    async with httpx.AsyncClient() as client:
        try:
            x_sqlbot_token = get_token(create_chat=False)["access_token"]
            headers = {"X-Sqlbot-Token": x_sqlbot_token}
            logger.info(f"Sending request to {sqlbot_base_url}/openapi/getDataSourceList with headers: {headers}")

            response = await client.get(
                f"{sqlbot_base_url}/openapi/getDataSourceList",
                headers=headers
            )

            logger.info(f"Response status: {response.status_code}")
            if response.status_code != 200:
                error_msg = f"Failed to get database list: {response.text}"
                logger.error(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)

            result = response.json()
            logger.debug(f"Response data: {result}")

            if result.get("code") != 0:
                error_msg = f"Database list request failed: {result.get('msg', 'Unknown error')}"
                logger.error(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)

            logger.info(f"Successfully retrieved database list with {len(result.get('data', []))} databases")
            return result.get("data", [])
        except httpx.RequestError as e:
            error_msg = f"Request error: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        except Exception as e:
            error_msg = f"Error getting database list: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)


# But if you re-run the setup, the new endpoints will now be exposed.
mcp.setup_server()

if __name__ == "__main__":
    logger.info("Starting SQLBot MCP Server")

    import uvicorn
    import os

    port = int(os.getenv("PORT", 8080))  # 默认使用8080端口，可通过环境变量修改
    logger.info(f"Server starting on port {port}")

    uvicorn.run(app, host="0.0.0.0", port=port)
