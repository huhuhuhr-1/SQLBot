import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    app_name: str = "NiFi MCP Server"
    app_version: str = "1.0.0"

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 7000

    # 日志配置
    log_level: str = "INFO"

    # NiFi 配置
    nifi_base_url: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_nifi_config(self) -> bool:
        """验证 NiFi 配置是否完整"""
        return bool(self.nifi_base_url)


# 创建全局设置实例
settings = Settings()