"""工作台总览接口，对应前端 src/api/modules/dashboard.js。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.crud import dashboard as crud

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def get_dashboard_overview(db: Session = Depends(get_db)):
    return ok(crud.overview(db))


@router.get("/live")
def get_dashboard_live(db: Session = Depends(get_db)):
    """工作台 5s 轮询的实时字段：GPU 利用率/显存 + 进行中任务数 + 最近任务进度。"""
    return ok(crud.live(db))
