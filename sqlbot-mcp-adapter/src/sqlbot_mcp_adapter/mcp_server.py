"""MCP Server for SQLBot integration."""

import json
import logging
from typing import Any, Dict

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent
)

from .config import settings
from .models import DataSource
from .sqlbot_client import SQLBotClient

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server for SQLBot integration."""

    def __init__(self):
        self.server = Server(settings.mcp_server_name)
        self.sqlbot_client = SQLBotClient()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup MCP server handlers."""

        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List available tools."""
            tools = [
                Tool(
                    name="get_token",
                    description="获取 SQLBot 访问令牌",
                    inputSchema={
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
                ),
                Tool(
                    name="get_database_list",
                    description="获取数据源列表",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]
            return ListToolsResult(tools=tools)

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls."""
            try:
                if name == "get_token":
                    return await self._handle_get_token(arguments)
                elif name == "get_database_list":
                    return await self._handle_get_database_list(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error in tool {name}: {str(e)}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: {str(e)}"
                        )
                    ],
                    isError=True
                )

    async def _handle_get_token(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle get_token tool call."""
        try:
            create_chat = arguments.get("create_chat", True)
            token_data = await self.sqlbot_client.get_token_info(create_chat=create_chat)

            result = {
                "access_token": token_data.access_token,
                "token_type": token_data.token_type,
                "expire": token_data.expire,
                "chat_id": token_data.chat_id
            }

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Failed to get token: {str(e)}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Failed to get token: {str(e)}"
                    )
                ],
                isError=True
            )

    async def _handle_get_database_list(self, arguments: Dict[str, Any]) -> CallToolResult:
        """Handle get_database_list tool call."""
        try:
            databases = await self.sqlbot_client.get_database_list()

            # Convert to dict for JSON serialization
            db_list = []
            for db in databases:
                db_dict = {
                    "id": db.id,
                    "name": db.name,
                    "description": db.description,
                    "type": db.type,
                    "type_name": db.type_name,
                    "create_time": db.create_time.isoformat(),
                    "create_by": db.create_by,
                    "status": db.status,
                    "num": db.num,
                    "oid": db.oid
                }
                db_list.append(db_dict)

            result = {
                "databases": db_list,
                "count": len(db_list)
            }

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(result, indent=2, ensure_ascii=False)
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Failed to get database list: {str(e)}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Failed to get database list: {str(e)}"
                    )
                ],
                isError=True
            )

    async def close(self):
        """Close the MCP server and cleanup resources."""
        await self.sqlbot_client.close()

    def get_app(self):
        """Get the FastAPI app for HTTP mode."""
        return self.server.create_app()