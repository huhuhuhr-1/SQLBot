from typing import List, Optional
import json


class TableInfo:
    """表信息类"""

    def __init__(self, table_name: str, table_comment: str):
        self.table_name = table_name
        self.table_comment = table_comment

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "table_name": self.table_name,
            "table_comment": self.table_comment
        }


class DataSourceConfig:
    """数据源配置类"""

    def __init__(
            self,
            name: str,
            description: str,
            type: str,
            configuration: str,
            tables: List[TableInfo]
    ):
        self.name = name
        self.description = description
        self.type = type
        self.configuration = configuration
        self.tables = tables

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "configuration": self.configuration,
            "tables": [table.to_dict() for table in self.tables]
        }

    def to_json(self, indent: Optional[int] = 4) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'DataSourceConfig':
        """从字典创建实例"""
        tables = [TableInfo(**table) for table in data.get("tables", [])]
        return cls(
            name=data["name"],
            description=data["description"],
            type=data["type"],
            configuration=data["configuration"],
            tables=tables
        )


# 使用示例
if __name__ == "__main__":
    # 创建表信息
    table = TableInfo(table_name="test123", table_comment="agsga")

    # 创建数据源配置
    config = DataSourceConfig(
        name="172.28.147.208",
        description="172.28.147.208",
        type="pg",
        configuration="lALxGKFqFEr/kGdVSBWUHBfBTaAy0OIalD30epzAT1ElyOAvt/j7XJapAo3hiW3zlZyLBD6DLEL9NgGvdsVGVmwc1Kt/H8Kf0U45gzEdf8zVfxAkGUC8/QOjlm3f8zJcmKobZ26dSsF2YyhVFOzlmGqsN15BI5X7b1cLUtnuZutpB0QCwVDqBDzlLGKWBqugnz0AnbPEsgsVnYK/HnrB7zsElpV66KKEPVcFiNUYzqdxlIB5VLSpXmG3+l4iVICo6VHRQyVccosMVpSe77Xc+A==",
        tables=[table]
    )

    # 输出JSON格式
    print(config.to_json())
