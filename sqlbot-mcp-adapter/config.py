"""
应用配置管理模块

统一管理环境变量和应用配置，提供配置验证和默认值。
"""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""

    # SQLBot API 配置
    sqlbot_base_url: str = Field(
        default="http://localhost:8000/api/v1",
        env="SQLBOT_BASE_URL",
        description="SQLBot API 基础 URL"
    )
    sqlbot_username: str = Field(
        default="admin",
        env="SQLBOT_USERNAME",
        description="SQLBot 用户名"
    )
    sqlbot_password: str = Field(
        default="SQLBot@123456",
        env="SQLBOT_PASSWORD",
        description="SQLBot 密码"
    )

    # HTTP 服务器配置
    host: str = Field(
        default="0.0.0.0",
        env="HOST",
        description="HTTP 服务器主机地址"
    )
    port: int = Field(
        default=8080,
        env="PORT",
        description="HTTP 服务器端口"
    )

    # 日志配置
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="日志级别 (DEBUG/INFO/WARNING/ERROR)"
    )

    # 应用信息
    app_name: str = Field(
        default="SQLBot MCP Adapter",
        description="应用名称"
    )

    app_version: str = Field(
        default="1.0.0",
        description="应用版本"
    )

    # MCP 配置
    mcp_server_name: str = Field(
        default="sqlbot-adapter",
        env="MCP_SERVER_NAME",
        description="MCP 服务器名称"
    )

    # 令牌管理
    token_refresh_threshold: int = Field(
        default=300,
        env="TOKEN_REFRESH_THRESHOLD",
        description="令牌刷新阈值（秒）"
    )

    # CORS 配置
    all_cors_origins: Optional[str] = Field(
        default=None,
        env="ALL_CORS_ORIGINS",
        description="允许的 CORS 源（逗号分隔）"
    )

    # 数据库配置
    db_name: str = Field(
        default="人员台账",
        env="DB_NAME",
        description="默认数据库名称"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量

    def get_cors_origins(self) -> list[str]:
        """获取 CORS 源列表"""
        if not self.all_cors_origins:
            return ["*"]

        origins = [origin.strip() for origin in self.all_cors_origins.split(",")]
        return [origin for origin in origins if origin]

    def validate_sqlbot_config(self) -> bool:
        """验证 SQLBot 配置是否完整"""
        required_fields = [self.sqlbot_base_url, self.sqlbot_username, self.sqlbot_password]
        return all(field.strip() for field in required_fields)


# 全局配置实例
settings = Settings()
