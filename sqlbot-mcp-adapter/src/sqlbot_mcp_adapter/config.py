"""SQLBot MCP Adapter Configuration."""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""

    # SQLBot API Configuration
    sqlbot_base_url: str = Field(
        default="http://localhost:8000",
        description="SQLBot API base URL"
    )

    sqlbot_username: Optional[str] = Field(
        default=None,
        description="SQLBot username"
    )

    sqlbot_password: Optional[str] = Field(
        default=None,
        description="SQLBot password"
    )

    # MCP Server Configuration
    mcp_server_name: str = Field(
        default="sqlbot-adapter",
        description="MCP server name"
    )

    mcp_server_version: str = Field(
        default="1.0.0",
        description="MCP server version"
    )

    # HTTP Server Configuration
    host: str = Field(
        default="0.0.0.0",
        description="HTTP server host"
    )

    port: int = Field(
        default=8080,
        description="HTTP server port"
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    # Token Management
    token_refresh_threshold: int = Field(
        default=300,  # 5 minutes
        description="Token refresh threshold in seconds"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()