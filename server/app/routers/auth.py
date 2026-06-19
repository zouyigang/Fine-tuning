"""鉴权接口：登录 / 当前用户 / 登出。"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok, err
from app.core.security import verify_password, create_access_token
from app.core.oplog import record
from app.crud import user as user_crud
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginIn

router = APIRouter(prefix="/auth", tags=["auth"])


def _log_login(request: Request, db: Session, username: str, real_name, status: str, detail: str):
    ip = request.client.host if request.client else "-"
    record(db, username=username, real_name=real_name, module="系统", action="登录",
           method="POST", path="/api/auth/login", ip=ip, status=status, detail=detail)


@router.post("/login")
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = user_crud.get_by_username(db, body.username)
    if not user or not verify_password(body.password, user.password_hash):
        _log_login(request, db, body.username, None, "失败", "用户名或密码错误")
        return err("用户名或密码错误", code=4001)
    if user.status != "active":
        _log_login(request, db, user.username, user.real_name, "失败", "账号已被禁用")
        return err("账号已被禁用", code=4003)
    token = create_access_token(user.username)
    _log_login(request, db, user.username, user.real_name, "成功", "登录成功")
    return ok({"token": token, "user": user_crud.user_to_dict(user)})


@router.get("/me")
def me(current: User = Depends(get_current_user)):
    return ok(user_crud.user_to_dict(current))


@router.post("/logout")
def logout():
    # JWT 无状态，登出由前端清除 token 即可；如需服务端失效可接 Redis 黑名单（后续）
    return ok({"success": True})
