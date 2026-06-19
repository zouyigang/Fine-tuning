"""用户数据库读写。"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def user_to_dict(u: User) -> dict:
    """转成前端需要的结构（name/role/dept）。"""
    return {
        "id": u.id,
        "username": u.username,
        "name": u.real_name,
        "role": u.role,
        "dept": u.dept,
    }
