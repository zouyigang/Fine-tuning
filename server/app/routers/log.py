"""操作日志查询接口，对应前端 src/api/modules/log.js。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok, page
from app.crud import oplog as crud
from app.schemas.oplog import OperationLogOut

router = APIRouter(prefix="/log", tags=["log"])


@router.get("/list")
def get_log_list(
    username: str = "",
    module: str = "",
    keyword: str = "",
    status: str = "",
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_logs(db, username, module, keyword, status, page_no, page_size)
    return ok(page([OperationLogOut.model_validate(x) for x in items], total, page_no, page_size))


@router.get("/modules")
def get_log_modules(db: Session = Depends(get_db)):
    return ok(crud.distinct_modules(db))
