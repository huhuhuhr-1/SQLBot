
from typing import List
from pydantic import BaseModel, Field

from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.core.schemas import BaseCreatorDTO

class AiModelItem(BaseModel):
    name: str = Field(description=f"{PLACEHOLDER_PREFIX}model_name")
    model_type: int = Field(description=f"{PLACEHOLDER_PREFIX}model_type")
    base_model: str = Field(description=f"{PLACEHOLDER_PREFIX}base_model")
    supplier: int = Field(description=f"{PLACEHOLDER_PREFIX}supplier")
    protocol: int = Field(description=f"{PLACEHOLDER_PREFIX}protocol")
    default_model: bool = Field(default=False, description=f"{PLACEHOLDER_PREFIX}default_model")

class AiModelGridItem(AiModelItem, BaseCreatorDTO):
    pass

class AiModelConfigItem(BaseModel):
    key: str = Field(description=f"{PLACEHOLDER_PREFIX}arg_name")
    val: object = Field(description=f"{PLACEHOLDER_PREFIX}arg_val")
    name: str = Field(description=f"{PLACEHOLDER_PREFIX}arg_show_name")
    
class AiModelCreator(AiModelItem):
    api_domain: str = Field(description=f"{PLACEHOLDER_PREFIX}api_domain")
    api_key: str = Field(description=f"{PLACEHOLDER_PREFIX}api_key")
    config_list: List[AiModelConfigItem] = Field(description=f"{PLACEHOLDER_PREFIX}config_list")
    
class AiModelEditor(AiModelCreator, BaseCreatorDTO):
    pass


class AiModelExportItem(AiModelCreator):
    """单条 AI 模型导出结构，用于批量导入导出（不含 id）。"""
    pass


class AiModelExportPayload(BaseModel):
    """AI 模型批量导出响应 / 导入请求"""
    version: int = 1
    models: List[AiModelExportItem] = []