"""用户管理模块出入参 Schema（字段与前端 user.js 一致）。"""
from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    realName: str | None = None
    dept: str | None = None
    role: str | None = None
    status: str | None = None

    @classmethod
    def from_user(cls, u):
        return cls(id=u.id, username=u.username, realName=u.real_name,
                   dept=u.dept, role=u.role, status=u.status)


class UserCreate(BaseModel):
    username: str
    password: str
    realName: str | None = None
    dept: str | None = None
    role: str | None = "普通用户"


class UserUpdate(BaseModel):
    realName: str | None = None
    dept: str | None = None
    role: str | None = None


class PasswordResetIn(BaseModel):
    password: str


class UserStatusIn(BaseModel):
    status: str  # active / disabled
