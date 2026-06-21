"""用户数据库读写。"""
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.security import hash_password
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


# ---- 用户管理 CRUD ----
def list_users(db: Session, keyword: str = "", role: str = "", status: str = "",
               page: int = 1, page_size: int = 10):
    stmt = select(User)
    if keyword:
        stmt = stmt.where(
            (User.username.like(f"%{keyword}%")) | (User.real_name.like(f"%{keyword}%"))
        )
    if role:
        stmt = stmt.where(User.role == role)
    if status:
        stmt = stmt.where(User.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all(), total


def create_user(db: Session, payload: dict):
    """创建用户；用户名已存在返回 None。"""
    if get_by_username(db, payload["username"]):
        return None
    u = User(
        username=payload["username"],
        password_hash=hash_password(payload["password"]),
        real_name=payload.get("realName"),
        dept=payload.get("dept"),
        role=payload.get("role") or "普通用户",
        status="active",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def update_user(db: Session, user_id: int, payload: dict):
    u = db.get(User, user_id)
    if not u:
        return None
    if payload.get("realName") is not None:
        u.real_name = payload["realName"]
    if payload.get("dept") is not None:
        u.dept = payload["dept"]
    if payload.get("role") is not None:
        u.role = payload["role"]
    db.commit()
    db.refresh(u)
    return u


def delete_user(db: Session, user_id: int) -> bool:
    u = db.get(User, user_id)
    if not u:
        return False
    db.delete(u)
    db.commit()
    return True


def reset_password(db: Session, user_id: int, new_password: str) -> bool:
    u = db.get(User, user_id)
    if not u:
        return False
    u.password_hash = hash_password(new_password)
    db.commit()
    return True


def set_status(db: Session, user_id: int, status: str) -> bool:
    u = db.get(User, user_id)
    if not u:
        return False
    u.status = status
    db.commit()
    return True
