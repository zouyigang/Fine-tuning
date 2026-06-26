"""数据可视化大屏接口，对应前端 src/api/modules/screen.js。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.crud import screen as crud

router = APIRouter(prefix="/screen", tags=["screen"])


@router.get("/overview")
def get_screen_overview(db: Session = Depends(get_db)):
    """大屏全量快照（各业务表实时聚合）。"""
    return ok(crud.overview(db))
