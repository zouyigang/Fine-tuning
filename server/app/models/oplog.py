"""操作日志（审计）ORM 模型。"""
from sqlalchemy import Column, Integer, String

from app.core.database import Base


class OperationLog(Base):
    __tablename__ = "operation_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64))            # 操作账号
    realName = Column("real_name", String(64))  # 操作人姓名
    module = Column(String(32))              # 业务模块
    action = Column(String(64))              # 操作描述
    method = Column(String(8))               # HTTP 方法
    path = Column(String(255))               # 请求路径
    ip = Column(String(64))                  # 来源 IP
    status = Column(String(8))               # 成功 / 失败
    detail = Column(String(512))             # 补充信息
    time = Column(String(32))                # 操作时间
