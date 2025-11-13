"""Simple HTTP Server for testing basic functionality without MCP dependencies."""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SQLBot MCP Adapter",
    description="Simple test server for SQLBot integration",
    version="1.0.0"
)

# Temporary in-memory storage for testing
token_store = {}

class TokenRequest(BaseModel):
    username: str
    password: str
    create_chat: bool = True

class TokenResponse(BaseModel):
    code: int
    data: Optional[Dict[str, Any]] = None
    msg: Optional[str] = None

class DataSourceResponse(BaseModel):
    code: int
    data: Optional[list] = None
    msg: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "SQLBot MCP Adapter",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "sqlbot-mcp-adapter",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/mcp")
async def mcp_endpoint(request: Dict[str, Any]):
    """Simple MCP-compatible endpoint for testing."""
    try:
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": settings.mcp_server_name,
                        "version": settings.mcp_server_version
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": "get_token",
                            "description": "获取 SQLBot 访问令牌",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "create_chat": {
                                        "type": "boolean",
                                        "description": "是否创建chatId，默认为true",
                                        "default": True
                                    }
                                },
                                "required": []
                            }
                        },
                        {
                            "name": "get_database_list",
                            "description": "获取数据源列表",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "get_token":
                return await handle_get_token(arguments, request.get("id"))
            elif tool_name == "get_database_list":
                return await handle_get_database_list(arguments, request.get("id"))
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }

        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Unknown method: {method}"
                }
            }

    except Exception as e:
        logger.error(f"Error in MCP endpoint: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }

async def handle_get_token(arguments: Dict[str, Any], request_id: str = None):
    """Handle get_token tool call (mock implementation)."""
    try:
        create_chat = arguments.get("create_chat", True)

        # Mock token generation for testing
        mock_token = {
            "access_token": f"bearer mock_token_{datetime.now().timestamp()}",
            "token_type": "bearer",
            "expire": (datetime.now().timestamp() + 3600),
            "chat_id": "mock_chat_id" if create_chat else None
        }

        result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(mock_token, indent=2, ensure_ascii=False)
                }
            ]
        }

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": f"Failed to get token: {str(e)}"
            }
        }

async def handle_get_database_list(arguments: Dict[str, Any], request_id: str = None):
    """Handle get_database_list tool call (mock implementation)."""
    try:
        # Mock database list for testing
        mock_databases = [
            {
                "id": 1,
                "name": "人员台账",
                "description": "人员台账",
                "type": "excel",
                "type_name": "Excel/CSV",
                "create_time": datetime.now().isoformat(),
                "create_by": 1,
                "status": "Success",
                "num": "1/3",
                "oid": 1
            }
        ]

        result = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "databases": mock_databases,
                        "count": len(mock_databases)
                    }, indent=2, ensure_ascii=False)
                }
            ]
        }

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }

    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32603,
                "message": f"Failed to get database list: {str(e)}"
            }
        }

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting SQLBot MCP Adapter (Simple Mode) on {settings.host}:{settings.port}")
    uvicorn.run(
        "simple_server:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower()
    )