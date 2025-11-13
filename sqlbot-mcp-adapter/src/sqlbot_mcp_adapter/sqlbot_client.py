"""SQLBot API Client."""

import logging
from datetime import datetime, timedelta
from typing import Optional, List

import httpx
from .config import settings
from .models import (
    TokenRequest,
    TokenResponse,
    TokenData,
    DataSourceListResponse,
    DataSource
)

logger = logging.getLogger(__name__)


class SQLBotClient:
    """SQLBot API client with automatic token management."""

    def __init__(self):
        self.base_url = settings.sqlbot_base_url.rstrip('/')
        self.username = settings.sqlbot_username
        self.password = settings.sqlbot_password
        self._token_data: Optional[TokenData] = None
        self._token_expires_at: Optional[datetime] = None
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    def _is_token_expired(self) -> bool:
        """Check if the current token is expired or about to expire."""
        if not self._token_expires_at:
            return True

        threshold = timedelta(seconds=settings.token_refresh_threshold)
        return datetime.now() + threshold >= self._token_expires_at

    async def _get_token(self, create_chat: bool = True) -> TokenData:
        """Get a new access token."""
        if not self.username or not self.password:
            raise ValueError("SQLBot username and password are required")

        logger.info("Getting new access token")

        request_data = TokenRequest(
            username=self.username,
            password=self.password,
            create_chat=create_chat
        )

        response = await self.client.post(
            f"{self.base_url}/openapi/getToken",
            json=request_data.dict()
        )

        if response.status_code == 400:
            raise Exception("账号或工作空间异常")

        response.raise_for_status()

        token_response = TokenResponse(**response.json())
        if token_response.code != 0:
            raise Exception(f"Failed to get token: {token_response.msg}")

        if not token_response.data:
            raise Exception("No token data received")

        token_data = TokenData(**token_response.data)
        self._token_data = token_data

        # Parse expiration time
        try:
            self._token_expires_at = datetime.strptime(
                token_data.expire,
                "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            logger.warning("Could not parse token expiration time, assuming 1 hour")
            self._token_expires_at = datetime.now() + timedelta(hours=1)

        logger.info("Successfully obtained access token")
        return token_data

    async def get_valid_token(self, create_chat: bool = True) -> str:
        """Get a valid access token, refreshing if necessary."""
        if not self._token_data or self._is_token_expired():
            await self._get_token(create_chat=create_chat)

        return self._token_data.access_token

    async def get_database_list(self) -> List[DataSource]:
        """Get the list of available data sources."""
        logger.info("Getting database list")

        token = await self.get_valid_token(create_chat=False)

        headers = {
            "X-Sqlbot-Token": token,
            "Content-Type": "application/json"
        }

        response = await self.client.get(
            f"{self.base_url}/openapi/getDataSourceList",
            headers=headers
        )

        response.raise_for_status()

        data_response = DataSourceListResponse(**response.json())
        if data_response.code != 0:
            raise Exception(f"Failed to get database list: {data_response.msg}")

        if not data_response.data:
            return []

        logger.info(f"Successfully retrieved {len(data_response.data)} databases")
        return data_response.data

    async def get_token_info(self, create_chat: bool = True) -> TokenData:
        """Get token information (for MCP tool)."""
        return await self._get_token(create_chat=create_chat)