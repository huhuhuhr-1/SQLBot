"""Main entry point for SQLBot MCP Adapter."""

import argparse
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from .config import settings
from .mcp_server import MCPServer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Initialize MCP server
    mcp_server = MCPServer()
    app.state.mcp_server = mcp_server
    logger.info("SQLBot MCP Adapter started")

    try:
        yield
    finally:
        # Cleanup
        await mcp_server.close()
        logger.info("SQLBot MCP Adapter stopped")


def create_http_app() -> FastAPI:
    """Create FastAPI app for HTTP mode."""
    mcp_server = MCPServer()
    app = mcp_server.get_app()

    # Add lifespan manager
    @asynccontextmanager
    async def lifespan_wrapper(app: FastAPI):
        app.state.mcp_server = mcp_server
        logger.info("SQLBot MCP Adapter started in HTTP mode")

        try:
            yield
        finally:
            await mcp_server.close()
            logger.info("SQLBot MCP Adapter stopped")

    app.router.lifespan_context = lifespan_wrapper

    # Add health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "sqlbot-mcp-adapter"}

    return app


async def run_stdio_mode():
    """Run in stdio mode for local development."""
    logger.info("Starting SQLBot MCP Adapter in stdio mode")

    mcp_server = MCPServer()

    try:
        # Run the MCP server using stdio transport
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=settings.mcp_server_name,
                    server_version=settings.mcp_server_version,
                    capabilities=mcp_server.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None,
                    ),
                ),
            )
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Error in stdio mode: {str(e)}")
        sys.exit(1)
    finally:
        await mcp_server.close()


def run_http_mode(host: str = None, port: int = None):
    """Run in HTTP mode for remote deployment."""
    host = host or settings.host
    port = port or settings.port

    logger.info(f"Starting SQLBot MCP Adapter in HTTP mode on {host}:{port}")

    app = create_http_app()

    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=settings.log_level.lower()
        )
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Error in HTTP mode: {str(e)}")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SQLBot MCP Adapter")
    parser.add_argument(
        "--mode",
        choices=["stdio", "http"],
        default="http",
        help="运行模式: stdio (本地开发) 或 http (远程部署)"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="HTTP服务器主机地址 (仅HTTP模式)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="HTTP服务器端口 (仅HTTP模式)"
    )

    args = parser.parse_args()

    if args.mode == "stdio":
        asyncio.run(run_stdio_mode())
    else:
        run_http_mode(args.host, args.port)


if __name__ == "__main__":
    main()