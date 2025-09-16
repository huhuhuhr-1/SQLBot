# Author: Junjun
# Date: 2025/7/16

from enum import Enum


class ConnectType(Enum):
    sqlalchemy = ('sqlalchemy')
    py_driver = ('py_driver')

    def __init__(self, type_name):
        self.type_name = type_name


class DB(Enum):
    mysql = ('mysql', '`', '`', ConnectType.sqlalchemy)
    sqlServer = ('sqlServer', '[', ']', ConnectType.sqlalchemy)
    pg = ('pg', '"', '"', ConnectType.sqlalchemy)
    excel = ('excel', '"', '"', ConnectType.sqlalchemy)
    oracle = ('oracle', '"', '"', ConnectType.sqlalchemy)
    ck = ('ck', '"', '"', ConnectType.sqlalchemy)
    dm = ('dm', '"', '"', ConnectType.py_driver)
    doris = ('doris', '`', '`', ConnectType.py_driver)
    redshift = ('redshift', '"', '"', ConnectType.py_driver)
    es = ('es', '"', '"', ConnectType.py_driver)

    def __init__(self, type, prefix, suffix, connect_type: ConnectType):
        self.type = type
        self.prefix = prefix
        self.suffix = suffix
        self.connect_type = connect_type

    @classmethod
    def get_db(cls, type):
        for db in cls:
            if db.type == type:
                return db
        raise ValueError(f"Invalid db type: {type}")
