"""数据可视化大屏聚合：从各业务表实时汇总大屏所需全部面板数据。

对应前端 src/views/screen/index.vue 的数据结构
（headline / spotlight / taskTrend / datasetDist / annotation /
radar / gpuNodes / release / logs / tasks）。

所有数值均来自真实表聚合；个别无独立数据源的维度按「聚合可得 + 降级占位」
处理，不再用 Math.random 造数。前端页面与 8s 轮询逻辑无需改动。
"""
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import Dataset, AnnotationTask
from app.models.task import TrainTask
from app.models.model_version import ModelVersion, GrayRelease, DeployTarget
from app.models.evaluation import EvalTask
from app.models.config import ClusterInfo
from app.models.oplog import OperationLog


def _date_prefix(s):
    """从 '2026-06-05 03:30' 之类字符串取 date；失败返回 None。"""
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def task_trend(db: Session, days: int = 14) -> dict:
    """近 N 天微调任务「新建 / 完成」计数（真实：按 createdAt / finishedAt 日期聚合）。

    工作台与大屏共用此函数。窗口锚定当前日期，反映真实数据；
    无数据的日期即为 0（不再随机填充）。
    """
    today = datetime.now().date()
    window = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    idx = {d: i for i, d in enumerate(window)}
    created = [0] * days
    finished = [0] * days
    for t in db.scalars(select(TrainTask)).all():
        cd = _date_prefix(t.createdAt)
        if cd in idx:
            created[idx[cd]] += 1
        # 「完成」只计真正训练成功的任务；失败/停止虽也会写 finishedAt，不计入
        if t.status == "success":
            fd = _date_prefix(t.finishedAt)
            if fd in idx:
                finished[idx[fd]] += 1
    return {"dates": [f"{d.month}/{d.day}" for d in window], "created": created, "finished": finished}


def _new_ratio_str(rows, attr, total, days=7, is_datetime=False) -> float:
    """近 days 天新增占比（%），用于指标卡的环比指示。无总量返回 0。"""
    if not total:
        return 0.0
    cutoff = datetime.now() - timedelta(days=days)
    n = 0
    for r in rows:
        v = getattr(r, attr, None)
        if is_datetime:
            if v and v >= cutoff:
                n += 1
        else:
            d = _date_prefix(v)
            if d and d > cutoff.date():
                n += 1
    return round(n / total * 100, 1)


def _nodes_from_targets(db: Session) -> list[dict]:
    """sim 模式下的「集群负载」降级来源：用真实部署目标的负载率。

    部署目标 load_pct 为真实写入值；显存维度无独立来源，用负载率占位。
    """
    out = []
    for t in db.scalars(select(DeployTarget).where(DeployTarget.status == "在线")).all():
        load = t.load or 0
        out.append({"name": t.name, "util": load, "mem": load})
    return out


def gpu_summary(db: Session):
    """统一 GPU 利用率来源，供大屏与工作台共用。

    返回 (used_gpu, total_gpu, gpu_pct, nodes)。real 模式取真实 pynvml（各卡利用率均值）；
    否则回退集群配置 cluster_info（清库后无该行则为 0）。
    """
    nodes = _gpu_nodes(db)
    if settings.ENGINE_MODE == "real" and nodes:
        total = len(nodes)
        used = sum(1 for n in nodes if (n.get("util") or 0) > 5)
        pct = round(sum((n.get("util") or 0) for n in nodes) / total)
        return used, total, pct, nodes
    cluster = db.scalars(select(ClusterInfo).limit(1)).first()
    used = cluster.usedGpu if cluster else 0
    total = cluster.totalGpu if cluster else 0
    pct = round(used / total * 100) if total else 0
    return used, total, pct, nodes


def gpu_realtime(db: Session) -> dict:
    """实时 GPU 指标：计算利用率(峰值采样) + 显存占用(绝对 GB + 百分比)。

    供工作台 GPU 卡片轮询。real 模式走真实 pynvml；否则回退 cluster_info（无真实显存）。
    """
    util = mem_used = mem_total = used = total = 0
    if settings.ENGINE_MODE == "real":
        try:
            from app.services.engine import manager
            gs = [g for g in manager.gpu_status() if "error" not in g]
            if gs:
                total = len(gs)
                used = sum(1 for g in gs if (g.get("util") or 0) > 5)
                util = round(sum((g.get("util") or 0) for g in gs) / total)
                mem_used = sum(g.get("memUsedMB") or 0 for g in gs)
                mem_total = sum(g.get("memTotalMB") or 0 for g in gs)
        except Exception:
            pass
    if total == 0:  # 回退集群配置（清库后通常无该行 → 全 0）
        cluster = db.scalars(select(ClusterInfo).limit(1)).first()
        if cluster:
            used, total = cluster.usedGpu or 0, cluster.totalGpu or 0
            util = round(used / total * 100) if total else 0
    mem_pct = round(mem_used / mem_total * 100) if mem_total else 0
    used_gb, total_gb = round(mem_used / 1024, 1), round(mem_total / 1024, 1)
    sub = f"显存 {used_gb}/{total_gb} GB · {mem_pct}%" if mem_total else "显存 —"
    return {"util": util, "gpuUsed": used, "gpuTotal": total,
            "memUsedMB": mem_used, "memTotalMB": mem_total,
            "memUsedGB": used_gb, "memTotalGB": total_gb, "memPct": mem_pct, "sub": sub}


def _gpu_nodes(db: Session) -> list[dict]:
    if settings.ENGINE_MODE == "real":
        try:
            from app.services.engine import manager
            nodes = []
            for g in manager.gpu_status():
                if "error" in g:
                    continue
                mem_pct = round(g["memUsedMB"] / g["memTotalMB"] * 100) if g.get("memTotalMB") else 0
                nodes.append({"name": g.get("name") or f"GPU-{g.get('index')}",
                              "util": g.get("util", 0), "mem": mem_pct})
            if nodes:
                return nodes
        except Exception:
            pass
    return _nodes_from_targets(db)


# 训练任务状态 → 大屏状态色
_SMAP = {"running": "running", "success": "finished", "pending": "queued",
         "paused": "queued", "failed": "failed", "stopped": "failed"}


def overview(db: Session) -> dict:
    datasets = db.scalars(select(Dataset)).all()
    tasks_all = db.scalars(select(TrainTask)).all()
    models_all = db.scalars(select(ModelVersion)).all()

    ds_total = len(datasets)
    task_total = len(tasks_all)
    online = sum(1 for m in models_all if m.status == "online")
    samples = sum(d.total or 0 for d in datasets)

    ds_trend = _new_ratio_str(datasets, "created_at", ds_total, is_datetime=True)
    headline = [
        {"key": "datasets", "label": "数据集总量", "value": ds_total, "unit": "个", "trend": ds_trend, "up": True},
        {"key": "tasks", "label": "累计微调任务", "value": task_total, "unit": "个",
         "trend": _new_ratio_str(tasks_all, "createdAt", task_total), "up": True},
        {"key": "models", "label": "在线服务模型", "value": online, "unit": "个",
         "trend": _new_ratio_str(models_all, "trainAt", len(models_all)), "up": True},
        {"key": "samples", "label": "标注样本累计", "value": int(samples), "unit": "条", "trend": ds_trend, "up": True},
    ]

    # ---- spotlight 三大主指标 ----
    today = datetime.now().date()
    today_tasks = sum(1 for t in tasks_all if _date_prefix(t.createdAt) == today)
    running = sum(1 for t in tasks_all if t.status == "running")
    f1s = [m.f1 for m in models_all if m.f1 is not None]
    avg_acc = round(sum(f1s) / len(f1s) * 100, 1) if f1s else 0

    # GPU 利用率：real 模式取真实 pynvml（各卡均值）；否则回退集群配置（cluster_info）。
    used_gpu, total_gpu, gpu_pct, gpu_nodes = gpu_summary(db)
    spotlight = [
        {"label": "今日训练任务", "value": today_tasks, "unit": "个", "sub": f"运行中 {running}"},
        {"label": "模型平均准确率", "value": avg_acc, "unit": "%", "sub": f"在线模型 {online} 个"},
        {"label": "GPU 集群利用率", "value": gpu_pct, "unit": "%", "sub": f"在用 {used_gpu}/{total_gpu} 卡"},
    ]

    # ---- 数据集类型分布（真实 group by）----
    dist_rows = db.execute(select(Dataset.type, func.count()).group_by(Dataset.type)).all()
    dataset_dist = [{"name": t or "未分类", "value": c} for t, c in dist_rows]

    # ---- 各部门标注进度（annotation_task 关联 dataset.dept 取均值）----
    ds_dept = {d.id: d.dept for d in datasets}
    agg = defaultdict(lambda: [0, 0])
    for a in db.scalars(select(AnnotationTask)).all():
        dept = ds_dept.get(a.dataset_id) or "其他"
        prog = round(a.done / a.total * 100) if a.total else 0
        agg[dept][0] += prog
        agg[dept][1] += 1
    annotation = sorted(
        [{"name": dept, "value": round(s / c)} for dept, (s, c) in agg.items() if c],
        key=lambda x: -x["value"])[:6]

    # ---- 模型效果评估雷达（各类型 F1 均值，真实）----
    radar_rows = db.execute(
        select(EvalTask.modelType, func.avg(EvalTask.f1)).group_by(EvalTask.modelType)).all()
    radar = {
        "indicators": [{"name": mt or "其他", "max": 100} for mt, _ in radar_rows],
        "series": [{"name": "各类型 F1 均值", "value": [round((f or 0) * 100, 1) for _, f in radar_rows]}],
    }

    # ---- 模型上线流水（灰度中 + 在线全量，真实）----
    release = []
    for g in db.scalars(select(GrayRelease).where(GrayRelease.status == "灰度中")).all():
        release.append({"name": g.name, "stage": "灰度", "percent": g.traffic or 0, "color": "#faad14"})
    for m in db.scalars(select(ModelVersion).where(ModelVersion.status == "online").limit(4)).all():
        release.append({"name": f"{m.name} {m.version}", "stage": "全量", "percent": 100, "color": "#52c41a"})

    # ---- 实时操作流水（直接读 operation_log，真实）----
    logs = []
    for o in db.scalars(select(OperationLog).order_by(OperationLog.id.desc()).limit(14)).all():
        level = {"成功": "success", "失败": "danger"}.get(o.status, "info")
        text = o.action + (f" · {o.detail}" if o.detail else "")
        logs.append({"id": o.id, "time": (o.time or "")[-8:], "actor": o.realName or o.username,
                     "module": o.module or "系统", "text": text, "level": level})

    # ---- 微调任务运行状态（真实）----
    tasks = []
    q = db.scalars(
        select(TrainTask)
        .where(TrainTask.status.in_(["running", "pending", "paused", "failed", "success"]))
        .order_by(TrainTask.id.desc()).limit(8)).all()
    for t in q:
        tasks.append({"id": f"T-{t.id}", "name": t.name, "base": t.baseModel or "-",
                      "gpu": t.gpu or "-", "loss": t.loss or "-", "progress": t.progress or 0,
                      "status": _SMAP.get(t.status, "queued"), "eta": "—"})

    return {
        "headline": headline, "spotlight": spotlight, "taskTrend": task_trend(db),
        "datasetDist": dataset_dist, "annotation": annotation, "radar": radar,
        "gpuNodes": gpu_nodes, "release": release, "logs": logs, "tasks": tasks,
    }
