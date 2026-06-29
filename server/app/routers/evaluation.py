"""模型效果评估接口，路径与前端 src/api/modules/evaluation.js 对应。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import storage
from app.core.database import get_db
from app.core.response import ok, err, page
from app.crud import evaluation as crud
from app.deps import get_current_user
from app.models.user import User
from app.schemas.evaluation import (
    EvalTaskOut, ReviewSampleOut, ErrorCaseOut, EvalReportOut,
    ReportGenIn, ReviewSubmitIn, EvalRunIn, SceneRunIn, ReviewSampleIn,
)
from app.services import reporting
from app.services.eval_engine import runner as eval_runner

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/list")
def get_eval_list(
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_eval_tasks(db, page_no, page_size)
    return ok(page([EvalTaskOut.model_validate(x) for x in items], total, page_no, page_size))


@router.get("/metrics")
def get_metrics(modelType: str = "ner", db: Session = Depends(get_db)):
    return ok(crud.metrics(db, modelType))


@router.post("/run")
def run_evaluation(
    body: EvalRunIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """真跑评估：加载所选模型版本，在已发布测试集上推理算指标并落库。"""
    creator = current.real_name or current.username
    try:
        result = eval_runner.start(body.modelId, body.datasetId, body.limit, creator)
    except Exception as e:
        return err(f"启动评估失败：{e}", code=4001)
    return ok(result)


@router.get("/run/{eval_task_id}")
def get_evaluation_run(eval_task_id: int, db: Session = Depends(get_db)):
    """轮询评估进度 / 结果。"""
    status = eval_runner.status(db, eval_task_id)
    if not status:
        return err("评估任务不存在", code=4004)
    return ok(status)


@router.get("/benchmark")
def get_benchmark(db: Session = Depends(get_db)):
    return ok(crud.benchmark(db))


@router.post("/benchmark/run")
def run_benchmark(
    body: EvalRunIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """真跑基准对比：所选微调版本 vs 其基座模型，在同一已发布测试集上各评估一遍。"""
    creator = current.real_name or current.username
    try:
        result = eval_runner.start_benchmark(body.modelId, body.datasetId, body.limit, creator)
    except Exception as e:
        return err(f"启动基准对比失败：{e}", code=4001)
    return ok(result)


@router.get("/benchmark/run/{eval_task_id}")
def get_benchmark_run(eval_task_id: int, db: Session = Depends(get_db)):
    """轮询基准对比进度。"""
    status = eval_runner.status(db, eval_task_id)
    if not status:
        return err("对比任务不存在", code=4004)
    return ok(status)


@router.get("/scene-validation")
def get_scene_validation(db: Session = Depends(get_db)):
    return ok(crud.scene_validation(db))


@router.post("/scene/run")
def run_scene_validation(
    body: SceneRunIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """真跑业务场景验证：所选模型在多个已发布测试集上各评估一遍，每个测试集记为一个场景。"""
    creator = current.real_name or current.username
    try:
        result = eval_runner.start_scene(body.modelId, body.datasetIds, body.limit, creator)
    except Exception as e:
        return err(f"启动场景验证失败：{e}", code=4001)
    return ok(result)


@router.get("/scene/run/{eval_task_id}")
def get_scene_run(eval_task_id: int, db: Session = Depends(get_db)):
    """轮询场景验证进度。"""
    status = eval_runner.status(db, eval_task_id)
    if not status:
        return err("场景验证任务不存在", code=4004)
    return ok(status)


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


@router.post("/review/sample")
def run_review_sampling(
    body: ReviewSampleIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """真模型对所选测试集抽样预测，入人工复核队列（待复核）。"""
    creator = current.real_name or current.username
    reviewer = body.reviewer or creator
    try:
        result = eval_runner.start_review(body.modelId, body.datasetId, body.count, reviewer, creator)
    except Exception as e:
        return err(f"启动复核抽样失败：{e}", code=4001)
    return ok(result)


@router.get("/review/run/{eval_task_id}")
def get_review_run(eval_task_id: int, db: Session = Depends(get_db)):
    """轮询复核抽样进度。"""
    status = eval_runner.status(db, eval_task_id)
    if not status:
        return err("复核抽样任务不存在", code=4004)
    return ok(status)


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


@router.delete("/reports/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db)):
    """删除一份评估报告。"""
    if not crud.delete_report(db, report_id):
        return err("报告不存在", code=4004)
    return ok({"deleted": report_id})


@router.post("/review-results")
def submit_review_results(body: ReviewSubmitIn, db: Session = Depends(get_db)):
    updated = crud.submit_review_results(db, [r.model_dump() for r in body.results])
    return ok({"updated": updated})


@router.get("/error-cases/export")
def export_error_cases(errorType: str = "", db: Session = Depends(get_db)):
    """导出错误案例为 Excel 文件。"""
    rows = crud.all_error_cases(db, errorType)
    data = reporting.error_cases_excel(rows)
    name = f"错误案例分析{('-' + errorType) if errorType else ''}.xlsx"
    _stored, abspath, _size = storage.save_bytes("reports", name, data)
    return storage.file_response(abspath, name, media_type=_XLSX_MIME)


@router.get("/reports/{report_id}/export")
def export_report(report_id: int, format: str = "pdf", db: Session = Depends(get_db)):
    """导出评估报告：format=pdf 生成 PDF，format=excel 生成 Excel。"""
    rep = crud.get_report(db, report_id)
    if not rep:
        return err("报告不存在", code=4004)
    if format == "excel":
        data = reporting.report_excel(rep)
        name, mime = f"{rep.name}.xlsx", _XLSX_MIME
    else:
        data = reporting.report_pdf(rep)
        name, mime = f"{rep.name}.pdf", "application/pdf"
    _stored, abspath, _size = storage.save_bytes("reports", name, data)
    return storage.file_response(abspath, name, media_type=mime)
