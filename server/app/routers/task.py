"""微调任务管理接口，路径与前端 src/api/modules/task.js 对应。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok, err, page
from app.crud import task as crud
from app.schemas.task import TaskOut, TaskCreate, StatusIn, ScheduleCreateIn, ScheduleReorderIn

router = APIRouter(prefix="/task", tags=["task"])


@router.get("/list")
def get_task_list(
    keyword: str = "",
    status: str = "",
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_tasks(db, keyword, status, page_no, page_size)
    return ok(page([TaskOut.model_validate(x) for x in items], total, page_no, page_size))


@router.get("/running")
def get_running_task(db: Session = Depends(get_db)):
    t = crud.current_running(db)
    if not t:
        return ok(None)
    return ok(crud.running_payload(db, t))


@router.get("/curve")
def get_training_curve(db: Session = Depends(get_db)):
    t = crud.current_running(db)
    if not t:
        return ok({"steps": [], "loss": [], "valLoss": [], "acc": [], "gpu": []})
    return ok(crud.training_curve(db, t))


@router.get("/resource-usage")
def get_resource_usage(db: Session = Depends(get_db)):
    t = crud.current_running(db)
    if not t:
        return ok({"points": [], "gpu": [], "cpu": [], "mem": []})
    return ok(crud.resource_usage(db, t))


@router.get("/logs")
def get_task_logs(
    taskId: int | None = None,
    level: str = "",
    keyword: str = "",
    db: Session = Depends(get_db),
):
    # 前端不传 taskId 时，默认取当前监控的运行任务
    if not taskId:
        t = crud.current_running(db)
        taskId = t.id if t else 1
    logs = crud.get_logs(db, taskId, level, keyword)
    return ok([{"id": l.id, "time": l.time, "level": l.level, "msg": l.msg} for l in logs])


@router.get("/schedule")
def get_schedule_queue(db: Session = Depends(get_db)):
    return ok(crud.schedule_queue(db))


@router.post("/schedule")
def create_schedule_item(payload: ScheduleCreateIn, db: Session = Depends(get_db)):
    item = crud.create_schedule_item(db, payload.model_dump(exclude_none=True))
    return ok({"id": item.id})


@router.put("/schedule/reorder")
def reorder_schedule(body: ScheduleReorderIn, db: Session = Depends(get_db)):
    updated = crud.reorder_schedule(db, body.ids)
    return ok({"updated": updated})


@router.delete("/schedule/{item_id}")
def remove_schedule_item(item_id: int, db: Session = Depends(get_db)):
    if not crud.remove_schedule_item(db, item_id):
        return err("调度项不存在", code=4004)
    return ok({"success": True})


@router.post("")
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    item = crud.create_task(db, payload.model_dump(exclude_none=True))
    return ok(TaskOut.model_validate(item))


@router.put("/{task_id}/status")
def update_task_status(task_id: int, body: StatusIn, db: Session = Depends(get_db)):
    if not crud.update_status(db, task_id, body.status):
        return err("任务不存在", code=4004)
    return ok({"success": True})
