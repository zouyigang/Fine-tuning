"""操作日志查询。"""
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from app.models.oplog import OperationLog


def list_logs(db: Session, username: str = "", module: str = "", keyword: str = "",
              status: str = "", page: int = 1, page_size: int = 10):
    stmt = select(OperationLog)
    if username:
        stmt = stmt.where(OperationLog.username.like(f"%{username}%"))
    if module:
        stmt = stmt.where(OperationLog.module == module)
    if status:
        stmt = stmt.where(OperationLog.status == status)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(
            OperationLog.action.like(like),
            OperationLog.path.like(like),
            OperationLog.detail.like(like),
            OperationLog.realName.like(like),
        ))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(OperationLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all(), total


def distinct_modules(db: Session):
    rows = db.scalars(select(OperationLog.module).distinct()).all()
    return [m for m in rows if m]
