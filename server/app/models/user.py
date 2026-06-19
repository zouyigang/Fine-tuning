"""用户/角色模型（P2 鉴权使用，先建表）。"""
from sqlalchemy import Column, Integer, String

from app.core.database import Base


class User(Base):
    __tablename__ = "sys_user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password_hash = Column(String(255))
    real_name = Column(String(32))
    dept = Column(String(32))
    role = Column(String(32))
    status = Column(String(16), default="active")
