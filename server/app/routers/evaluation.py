"""模型效果评估接口，路径与前端 src/api/modules/evaluation.js 对应。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok, page
from app.crud import evaluation as crud
from app.deps import get_current_user
from app.models.user import User
from app.schemas.evaluation import (
    EvalTaskOut, ReviewSampleOut, ErrorCaseOut, EvalReportOut,
    ReportGenIn, ReviewSubmitIn,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get("/list")
def get_eval_list(
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_eval_tasks(db, page_no, page_size)
    return ok(page([EvalTaskOut.model_validate(x) for x in items], total, page_no, page_size))


@router.get("/metrics")
def get_metrics(modelType: str = "ner"):
    return ok(crud.metrics(modelType))


@router.get("/benchmark")
def get_benchmark():
    return ok(crud.benchmark())


@router.get("/scene-validation")
def get_scene_validation():
    return ok(crud.scene_validation())


@router.get("/review-samples")
def get_review_samples(
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_review_samples(db, page_no, page_size)
    return ok(page([ReviewSampleOut.model_validate(x) for x in items], total, page_no, page_size))


@router.get("/review-summary")
def get_review_summary(db: Session = Depends(get_db)):
    return ok(crud.review_summary(db))


@router.get("/error-cases")
def get_error_cases(
    errorType: str = "",
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total, dist = crud.list_error_cases(db, errorType, page_no, page_size)
    result = page([ErrorCaseOut.model_validate(x) for x in items], total, page_no, page_size)
    result["dist"] = dist
    return ok(result)


@router.get("/reports")
def get_report_list(
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_reports(db, page_no, page_size)
    return ok(page([EvalReportOut.model_validate(x) for x in items], total, page_no, page_size))


@router.post("/reports")
def generate_report(
    body: ReportGenIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    creator = current.real_name or current.username
    rep = crud.create_report(db, model=body.model, creator=creator)
    return ok(EvalReportOut.model_validate(rep))


@router.post("/review-results")
def submit_review_results(body: ReviewSubmitIn, db: Session = Depends(get_db)):
    updated = crud.submit_review_results(db, [r.model_dump() for r in body.results])
    return ok({"updated": updated})
