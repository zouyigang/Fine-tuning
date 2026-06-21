"""用户管理接口，路径与前端 src/api/modules/user.js 对应。

写操作经 deps.enforce_rbac 拦截（需「权限分配」权限）；
为防自锁，禁止删除/禁用当前登录账号。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok, err, page
from app.crud import user as crud
from app.deps import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserOut, UserCreate, UserUpdate, PasswordResetIn, UserStatusIn,
)

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/list")
def get_user_list(
    keyword: str = "",
    role: str = "",
    status: str = "",
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_users(db, keyword, role, status, page_no, page_size)
    return ok(page([UserOut.from_user(x) for x in items], total, page_no, page_size))


@router.post("")
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    u = crud.create_user(db, payload.model_dump())
    if not u:
        return err("用户名已存在", code=4009)
    return ok(UserOut.from_user(u))


@router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)):
    u = crud.update_user(db, user_id, payload.model_dump(exclude_none=True))
    if not u:
        return err("用户不存在", code=4004)
    return ok(UserOut.from_user(u))


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if user_id == current.id:
        return err("不能删除当前登录账号", code=4003)
    if not crud.delete_user(db, user_id):
        return err("用户不存在", code=4004)
    return ok({"success": True})


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, body: PasswordResetIn, db: Session = Depends(get_db)):
    if not crud.reset_password(db, user_id, body.password):
        return err("用户不存在", code=4004)
    return ok({"success": True})


@router.put("/{user_id}/status")
def set_user_status(
    user_id: int,
    body: UserStatusIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if user_id == current.id and body.status != "active":
        return err("不能禁用当前登录账号", code=4003)
    if not crud.set_status(db, user_id, body.status):
        return err("用户不存在", code=4004)
    return ok({"success": True})
