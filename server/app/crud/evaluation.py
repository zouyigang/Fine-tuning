"""模型效果评估模块数据库读写 + 聚合分析。

列表类（评估任务/复核样本/错误案例/报告）直接读表；
自动化指标 / 基准对比 / 场景验证为聚合分析结果，由本层计算返回。
"""
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.evaluation import EvalTask, EvalReport, ReviewSample, ErrorCase


def _paginate(db: Session, stmt, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return rows, total


def list_eval_tasks(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(EvalTask).order_by(EvalTask.id.desc())
    return _paginate(db, stmt, page, page_size)


def list_review_samples(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(ReviewSample).order_by(ReviewSample.id.desc())
    return _paginate(db, stmt, page, page_size)


def review_summary(db: Session) -> dict:
    rows = db.scalars(select(ReviewSample)).all()
    total = len(rows)
    reviewed = sum(1 for r in rows if r.result != "待复核")
    correct = sum(1 for r in rows if r.result == "正确")
    pending = total - reviewed
    accuracy = round(correct / reviewed * 100, 1) if reviewed else 0
    return {"total": total, "reviewed": reviewed, "correct": correct,
            "accuracy": accuracy, "pending": pending}


def list_error_cases(db: Session, error_type: str = "", page: int = 1, page_size: int = 10):
    stmt = select(ErrorCase)
    if error_type:
        stmt = stmt.where(ErrorCase.errorType == error_type)
    stmt = stmt.order_by(ErrorCase.id.desc())
    rows, total = _paginate(db, stmt, page, page_size)
    # 错误类型分布（按 count 求和）
    dist_rows = db.execute(
        select(ErrorCase.errorType, func.sum(ErrorCase.count)).group_by(ErrorCase.errorType)
    ).all()
    dist = [{"name": name, "value": int(val or 0)} for name, val in dist_rows]
    return rows, total, dist


def list_reports(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(EvalReport).order_by(EvalReport.id.desc())
    return _paginate(db, stmt, page, page_size)


# ---- 聚合分析（静态/计算结果，不单独建表）----
_METRICS = {
    "ocr": [
        {"name": "字符准确率", "value": 98.6, "unit": "%"},
        {"name": "行准确率", "value": 95.2, "unit": "%"},
        {"name": "平均编辑距离", "value": 0.04, "unit": ""},
        {"name": "推理耗时", "value": 42, "unit": "ms"},
    ],
    "ner": [
        {"name": "精确率", "value": 94.8, "unit": "%"},
        {"name": "召回率", "value": 92.3, "unit": "%"},
        {"name": "F1 值", "value": 93.5, "unit": "%"},
        {"name": "实体类型数", "value": 12, "unit": "类"},
    ],
    "relation": [
        {"name": "三元组准确率", "value": 89.7, "unit": "%"},
        {"name": "关系召回率", "value": 87.1, "unit": "%"},
        {"name": "F1 值", "value": 88.4, "unit": "%"},
        {"name": "关系类型数", "value": 8, "unit": "类"},
    ],
    "event": [
        {"name": "事件识别准确率", "value": 91.2, "unit": "%"},
        {"name": "要素抽取 F1", "value": 88.9, "unit": "%"},
        {"name": "触发词准确率", "value": 90.5, "unit": "%"},
        {"name": "事件类型数", "value": 6, "unit": "类"},
    ],
}

_PER_CLASS = [
    {"label": "人名", "precision": 96.2, "recall": 95.1, "f1": 95.6},
    {"label": "组织机构", "precision": 93.4, "recall": 91.0, "f1": 92.2},
    {"label": "时间", "precision": 97.8, "recall": 96.5, "f1": 97.1},
    {"label": "地点", "precision": 92.1, "recall": 89.7, "f1": 90.9},
    {"label": "金额", "precision": 95.5, "recall": 94.2, "f1": 94.8},
    {"label": "案由", "precision": 86.3, "recall": 82.5, "f1": 84.4},
]


def metrics(model_type: str = "ner") -> dict:
    return {"metrics": _METRICS.get(model_type, _METRICS["ner"]), "perClass": _PER_CLASS}


def benchmark() -> dict:
    dims = ["精确率", "召回率", "F1 值", "推理速度", "鲁棒性"]
    cur = [94.8, 92.3, 93.5, 88, 90]
    prod = [91.2, 88.5, 89.8, 90, 85]
    hist = [93.0, 90.1, 91.5, 85, 88]
    return {
        "dims": dims,
        "models": [
            {"name": "本次微调模型", "values": cur},
            {"name": "当前生产模型", "values": prod},
            {"name": "历史最优模型", "values": hist},
        ],
        "compare": [
            {"dim": d, "current": cur[i], "prod": prod[i], "diff": round(cur[i] - prod[i], 1)}
            for i, d in enumerate(dims)
        ],
    }


def scene_validation() -> dict:
    cases = [
        {"id": 1, "caseNo": "（2026）刑侦字第 218 号", "type": "盗窃", "sampleCount": 120, "accuracy": 94.2, "hard": False},
        {"id": 2, "caseNo": "（2026）刑侦字第 365 号", "type": "诈骗", "sampleCount": 86, "accuracy": 91.5, "hard": True},
        {"id": 3, "caseNo": "（2026）刑侦字第 142 号", "type": "涉毒", "sampleCount": 64, "accuracy": 88.7, "hard": True},
        {"id": 4, "caseNo": "（2026）刑侦字第 507 号", "type": "经济犯罪", "sampleCount": 158, "accuracy": 95.6, "hard": False},
        {"id": 5, "caseNo": "（2026）刑侦字第 233 号", "type": "盗窃", "sampleCount": 102, "accuracy": 93.1, "hard": False},
        {"id": 6, "caseNo": "（2026）刑侦字第 419 号", "type": "诈骗", "sampleCount": 75, "accuracy": 86.4, "hard": True},
        {"id": 7, "caseNo": "（2026）刑侦字第 188 号", "type": "经济犯罪", "sampleCount": 140, "accuracy": 96.0, "hard": False},
        {"id": 8, "caseNo": "（2026）刑侦字第 321 号", "type": "涉毒", "sampleCount": 58, "accuracy": 89.3, "hard": True},
        {"id": 9, "caseNo": "（2026）刑侦字第 276 号", "type": "盗窃", "sampleCount": 110, "accuracy": 92.8, "hard": False},
        {"id": 10, "caseNo": "（2026）刑侦字第 460 号", "type": "经济犯罪", "sampleCount": 132, "accuracy": 94.9, "hard": False},
    ]
    return {
        "summary": {"total": 1280, "correct": 1186, "accuracy": 92.7, "hardCase": 156, "hardAccuracy": 78.2},
        "cases": cases,
    }
