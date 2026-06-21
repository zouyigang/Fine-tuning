"""依赖注入集中点。"""
import re

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db  # noqa: F401
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.models.config import SysRole
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


# ---- 接口层 RBAC ----
# (HTTP 方法, 路径正则, 所需权限名)；权限名取自 perm_catalog / sys_role.granted。
# 仅高风险写操作按角色拦截；其余写操作登录即可（权限目录无对应项）。
_RBAC_RULES = [
    ("POST", r"^/api/task$", "创建微调任务"),
    ("POST", r"^/api/config/hyper-templates$", "配置超参数"),
    ("DELETE", r"^/api/config/hyper-templates/\d+$", "配置超参数"),
    ("POST", r"^/api/config/resource-quotas$", "资源配额管理"),
    ("POST", r"^/api/config/role-permissions$", "权限分配"),
    ("POST", r"^/api/model/gray-releases$", "审批模型上线"),
    ("PUT", r"^/api/model/gray-releases/\d+/traffic$", "审批模型上线"),
    ("POST", r"^/api/model/\d+/release$", "审批模型上线"),
    ("POST", r"^/api/model/\d+/rollback$", "模型回滚"),
    # 用户管理：增删改、改密、启停均需「权限分配」
    ("POST", r"^/api/user$", "权限分配"),
    ("PUT", r"^/api/user/\d+$", "权限分配"),
    ("DELETE", r"^/api/user/\d+$", "权限分配"),
    ("POST", r"^/api/user/\d+/reset-password$", "权限分配"),
    ("PUT", r"^/api/user/\d+/status$", "权限分配"),
]


def _required_perm(method: str, path: str) -> str | None:
    for m, p, perm in _RBAC_RULES:
        if m == method and re.match(p, path):
            return perm
    return None


def enforce_rbac(
    request: Request,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """业务路由统一鉴权 + 按角色权限拦截高风险写操作。

    先确保已登录（依赖 get_current_user）；再查命中的 RBAC 规则：
    - 系统管理员：放行全部；
    - 其他角色：所需权限不在 sys_role.granted 中则抛 403。
    """
    perm = _required_perm(request.method.upper(), request.url.path)
    if perm is None or current.role == "系统管理员":
        return current
    role = db.scalar(select(SysRole).where(SysRole.role == current.role))
    granted = (role.granted if role else None) or []
    if perm not in granted:
        raise HTTPException(status_code=403, detail=f"无「{perm}」权限，操作被拒绝")
    return current
