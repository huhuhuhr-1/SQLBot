from typing import Generator
from contextlib import contextmanager

from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.orm import sessionmaker

from common.core.config import settings

# 优化数据库引擎配置，添加连接池设置
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_size=settings.PG_POOL_SIZE,  # 连接池大小
    max_overflow=settings.PG_MAX_OVERFLOW,  # 超出pool_size后最多可以创建的连接数
    pool_timeout=settings.PG_POOL_TIMEOUT,  # 等待连接池连接的超时时间（秒）
    pool_recycle=settings.PG_POOL_RECYCLE,  # 连接回收时间（秒）
    pool_pre_ping=settings.PG_POOL_PRE_PING,  # 每次从连接池获取连接时先测试连接是否有效
    pool_reset_on_return='rollback',  # 添加此配置确保连接返回时重置
    echo=settings.SQL_DEBUG  # 是否输出SQL语句到日志
)

# 创建会话工厂，用于创建新的会话
# SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """
    获取数据库会话 - 用于FastAPI依赖注入

    Yields:
        Session: 数据库会话对象
    """
    with Session(engine) as session:
        yield session


def get_session_direct() -> Session:
    """
    直接获取数据库会话（非生成器方式）

    Returns:
        Session: 数据库会话对象
    """
    return Session(engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    获取数据库会话的上下文管理器

    Yields:
        Session: 数据库会话对象
    """
    session = Session(engine)  # 直接使用 engine 创建会话
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """
    初始化数据库，创建所有定义的表
    """
    SQLModel.metadata.create_all(engine)


def close_engine():
    """
    关闭数据库引擎，释放所有连接
    """
    engine.dispose()
