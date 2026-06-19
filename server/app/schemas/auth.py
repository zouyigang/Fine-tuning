"""鉴权出入参 Schema。"""
from pydantic import BaseModel


class LoginIn(BaseModel):
    username: str
    password: str
