"""统一响应封装，结构与前端 src/api/request.js 拦截器约定一致：
成功 {code:0, data, message}；失败 {code!=0, data:null, message}。
"""
from typing import Any


def ok(data: Any = None, message: str = "ok") -> dict:
    return {"code": 0, "data": data, "message": message}


def err(message: str, code: int = 4000) -> dict:
    return {"code": code, "data": None, "message": message}


def page(items: list, total: int, page_no: int = 1, page_size: int = 10) -> dict:
    """分页结构，与前端 paginate() 输出一致。"""
    return {"list": items, "total": total, "page": page_no, "pageSize": page_size}
