# Author: Junjun
# Date: 2025/7/16

from enum import Enum


class DB(Enum):
    mysql = ('mysql', '`', '`')
    sqlServer = ('sqlServer', '[', ']')
    pg = ('pg', '"', '"')
    excel = ('excel', '"', '"')
    oracle = ('oracle', '"', '"')
    ck = ('ClickHouse', '"', '"')

    def __init__(self, type, prefix, suffix):
        self.type = type
        self.prefix = prefix
        self.suffix = suffix

    @classmethod
    def get_db(cls, type):
        for db in cls:
            if db.type == type:
                return db
        raise ValueError(f"Invalid db type: {type}")
