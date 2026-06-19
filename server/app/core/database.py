"""SQLAlchemy 引擎 / 会话 / Base。

默认 SQLite（开箱即跑），通过 .env 的 DATABASE_URL 可无缝切换到 MySQL。
ORM 模型使用通用类型，两种库均兼容。
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# SQLite 需要 check_same_thread=False 以配合 FastAPI 多线程
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：每个请求一个会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """建表（开发期用 create_all；生产用 Alembic 迁移，见 P6）。"""
    from app import models  # noqa: F401 确保所有模型已被导入注册
    Base.metadata.create_all(bind=engine)
