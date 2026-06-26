"""微调任务管理接口，路径与前端 src/api/modules/task.js 对应。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from starlette.responses import Response

from app.core.database import get_db
from app.core.response import ok, err, page
from app.crud import task as crud
from app.schemas.task import (
    TaskOut, TaskCreate, StatusIn, ScheduleCreateIn, ScheduleReorderIn, HyperApplyIn,
)

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


@router.get("/{task_id}/logs/download")
def download_task_logs(
    task_id: int,
    level: str = "",
    keyword: str = "",
    db: Session = Depends(get_db),
):
    """导出指定任务的训练日志为 .log 纯文本文件（可按级别/关键字过滤）。"""
    logs = crud.get_logs(db, task_id, level, keyword)
    lines = [f"{l.time} [{l.level}] {l.msg}" for l in logs]
    content = ("\n".join(lines) + "\n") if lines else "暂无日志\n"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="train-task-{task_id}.log"'},
    )


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
    # 闭环：只允许用「已发布」的数据集训练（已完成 标注→脱敏→发布，数据已脱敏且转成训练样本）。
    # 仅当引用到真实数据集行时校验；解析不到（自由文本/演示）放行，不破坏 sim 演示。
    from app.crud import dataset as ds_crud
    ds = ds_crud.resolve_for_training(db, payload.dataset)
    if ds is not None and ds.stage != "已发布":
        return err(f"数据集「{ds.name}」尚未发布（当前阶段：{ds.stage or '待标注'}），"
                   f"请先完成 标注→脱敏→发布 再用于训练", code=4001)
    # 双保险：数据集类型须与业务模型类型匹配（前端已过滤下拉，此处防接口直接绕过）
    mismatch, exp_label, act_label = ds_crud.model_dataset_type_mismatch(db, payload.modelType, ds)
    if mismatch:
        return err(f"业务模型「{payload.modelType}」需要「{exp_label}」类型的数据集，"
                   f"但所选「{ds.name}」是「{act_label}」类型，请重新选择匹配的数据集", code=4001)
    item = crud.create_task(db, payload.model_dump(exclude_none=True))
    return ok(TaskOut.model_validate(item))


@router.put("/{task_id}/status")
def update_task_status(task_id: int, body: StatusIn, db: Session = Depends(get_db)):
    from app.core.config import settings
    if settings.ENGINE_MODE == "real":
        from app.services.engine import manager
        # 继续/重试（前端发 running）：重置并重新入队，交调度器拉起
        if body.status == "running":
            if not crud.requeue_task(db, task_id):
                return err("任务不存在", code=4004)
            return ok({"success": True, "status": "pending"})
        # 暂停/终止：kill 子进程并记主动目标态（避免被收尾误判 failed）
        if body.status in ("paused", "stopped", "failed"):
            manager.stop_task(task_id, target_status=body.status)
    if not crud.update_status(db, task_id, body.status):
        return err("任务不存在", code=4004)
    return ok({"success": True})


@router.put("/{task_id}/hyperparams")
def apply_hyperparams(task_id: int, body: HyperApplyIn, db: Session = Depends(get_db)):
    """把超参配置应用到指定任务（pending/失败/暂停等非运行态可改）。"""
    ok_flag, msg = crud.apply_hyperparams(db, task_id, body.hyperparams, body.method)
    if not ok_flag:
        return err(msg, code=4003)
    return ok({"success": True})


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除训练任务（运行中/已产出模型版本的任务拒删；级联清理指标/日志/产物/调度项）。"""
    ok_flag, msg = crud.delete_task(db, task_id)
    if not ok_flag:
        return err(msg, code=4001)
    return ok({"success": True})


@router.get("/gpus")
def get_gpus():
    """真实引擎 GPU 状态（pynvml 实时采样）；sim 模式返回占位。"""
    from app.core.config import settings
    if settings.ENGINE_MODE != "real":
        return ok({"mode": "sim", "gpus": []})
    from app.services.engine import manager
    return ok({"mode": "real", "count": manager.gpu_count(),
               "concurrency": manager.concurrency(), "gpus": manager.gpu_status()})
