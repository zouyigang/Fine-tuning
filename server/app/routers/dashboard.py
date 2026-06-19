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
