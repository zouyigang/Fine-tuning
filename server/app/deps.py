"""依赖注入集中点。"""
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db  # noqa: F401
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.models.user import User


def get_current_user(
    authorization: str = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization: Bearer <token> 解析并返回当前用户，失败抛 401。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录，请先登录")
    token = authorization.split(" ", 1)[1]
    username = decode_access_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    user = user_crud.get_by_username(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user
