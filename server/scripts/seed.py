"""种子数据：把原前端 mock 的数据灌入数据库（全部模块）。

可独立运行：  python -m scripts.seed
也会在 main 启动时（AUTO_SEED=true 且库为空）自动调用 seed_if_empty()。
"""
import random

from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models.user import User
from app.models.dataset import (
    Dataset, DatasetVersion, DesensitizeRule, AnnotationTask, DatasetPermission, DatasetType,
)
from app.models.task import TrainTask, TrainLog
from app.models.evaluation import (
    EvalTask, EvalReport, ReviewSample, ErrorCase,
    EvalMetric, EvalPerClass, BenchmarkResult, SceneCase,
)
from app.models.model_version import ModelVersion, GrayRelease, ReleaseHistory, DeployTarget
from app.models.config import (
    BaseModelInfo, HyperTemplate, ResourceQuota, ClusterInfo,
    AutoTuneConfig, AutoTuneTrial, SysRole, PermCatalog, ConvertRule,
)
from app.models.oplog import OperationLog

# ---------- 通用 ----------
DEPTS = ["刑侦支队", "经侦支队", "网安支队", "情报中心"]
OWNERS = ["张三", "李四", "王五", "赵六"]
MODEL_TYPES = ["OCR 识别", "实体识别", "关系抽取", "事件构建", "风险预警", "路径分析"]


def rf(a, b, n=2):
    return round(random.uniform(a, b), n)


# ========== 数据集管理 ==========
DATA_TYPES = ["OCR 校对结果", "实体关系标注", "事件标注", "风险样本"]
DS_STATUS = ["标注中", "已完成", "待审核", "已归档"]
NAME_PREFIX = ["审讯笔录", "资金流水", "案件卷宗", "涉案人员", "风险预警"]

DEFAULT_VERSIONS = [
    ("v1.3", "补充 3200 条风险样本，修正实体边界", "张三", 48200, True, "2026-06-05 14:20"),
    ("v1.2", "完成关系三元组二次审核", "李四", 45000, False, "2026-05-22 09:10"),
    ("v1.1", "新增事件要素标注", "王五", 41000, False, "2026-05-08 16:40"),
    ("v1.0", "初始版本导入", "赵六", 32000, False, "2026-04-20 11:00"),
]
# (field, rule描述, sample, enabled, maskType)
DEFAULT_RULES = [
    ("身份证号", "保留前6后4，中间*", "110101********1234", True, "idcard"),
    ("手机号", "保留前3后4", "138****8888", True, "phone"),
    ("银行卡号", "仅保留后4位", "**** **** **** 6789", True, "bankcard"),
    ("姓名", "保留姓氏", "张**", True, "name"),
    ("家庭住址", "保留到区县", "北京市朝阳区****", False, "custom"),
    ("电子邮箱", "保留首字符与域名", "z***@example.com", False, "email"),
]


def seed_dataset(db):
    datasets = []
    for i in range(28):
        total = random.randint(2000, 50000)
        labeled = random.randint(int(total * 0.4), total)
        ds = Dataset(
            name=f"{random.choice(NAME_PREFIX)}数据集-2026{str(i + 1).zfill(3)}",
            type=random.choice(DATA_TYPES), dept=random.choice(DEPTS),
            total=total, labeled=labeled, progress=round(labeled / total * 100),
            version=f"v1.{random.randint(0, 6)}", desensitized=random.random() > 0.3,
            status=random.choice(DS_STATUS), owner=random.choice(OWNERS),
            updatedAt=f"2026-0{random.randint(1, 6)}-{random.randint(10, 28)} 1{random.randint(0, 5)}:30",
        )
        db.add(ds)
        datasets.append(ds)
    db.flush()
    for ds in datasets:
        for v in DEFAULT_VERSIONS:
            db.add(DatasetVersion(dataset_id=ds.id, version=v[0], desc=v[1], author=v[2],
                                  count=v[3], current=v[4], time=v[5]))
    for r in DEFAULT_RULES:
        db.add(DesensitizeRule(field=r[0], rule=r[1], sample=r[2], enabled=r[3], maskType=r[4]))
    for i in range(16):
        db.add(AnnotationTask(
            dataset_id=random.choice(datasets).id,
            title=f"{random.choice(['审讯笔录', '资金流水', '通话记录'])}标注任务-{i + 1}",
            type=random.choice(["OCR 文本校对", "实体/关系三元组", "事件要素", "风险行为"]),
            total=random.randint(100, 800), done=random.randint(0, 100),
            annotators=random.randint(1, 5),
            status=random.choice(["进行中", "待审核", "已完成"]),
            deadline=f"2026-06-{random.randint(10, 30)}"))
    for ds in datasets[:12]:
        db.add(DatasetPermission(
            dataset_id=ds.id, name=ds.name,
            secret="涉密" if ds.desensitized else "内部", dept=ds.dept,
            roles=["标注人员", "算法工程师"], canView=True,
            canEdit=random.random() > 0.5, canExport=random.random() > 0.6))
    return len(datasets)


# ========== 微调任务管理 ==========
TASK_STATUS = ["pending", "running", "paused", "success", "failed"]


def seed_task(db):
    for i in range(24):
        status = random.choice(TASK_STATUS)
        db.add(TrainTask(
            name=f"{random.choice(MODEL_TYPES)}微调-{20260600 + i}",
            modelType=random.choice(MODEL_TYPES),
            baseModel=random.choice(["Qwen2-7B", "Llama3-8B", "公安基座 v3", "GLM4-9B"]),
            dataset=f"审讯笔录数据集-2026{str(i + 1).zfill(3)}",
            status=status,
            progress=100 if status == "success" else (random.randint(10, 95) if status == "running" else random.randint(0, 60)),
            priority=random.choice(["高", "中", "低"]),
            gpu=f"{random.randint(1, 4)} × A100",
            epoch=f"{random.randint(1, 10)}/10",
            loss=str(rf(0.05, 0.6)),
            creator=random.choice(["张三", "李四", "王五"]),
            createdAt=f"2026-06-0{random.randint(1, 9)} 0{random.randint(1, 9)}:30",
            duration=f"{random.randint(1, 12)}h {random.randint(1, 59)}m"))
    levels = ["INFO", "WARN", "ERROR", "DEBUG"]
    msgs = [
        "Epoch 7 started, lr=2.0e-5", "step 13600 | loss=0.112 | acc=94.3%",
        "checkpoint saved at ./ckpt/epoch7-step13600.pt", "GPU memory usage 34.2GB / 40GB",
        "validation loss=0.108, f1=0.931", "WARN: gradient norm 5.21 exceeds threshold",
        "data loader prefetch 2 batches", "ERROR: NaN detected in loss, skipping batch 13721",
    ]
    for i in range(60):
        db.add(TrainLog(
            task_id=1,
            time=f"2026-06-08 1{random.randint(0, 5)}:{random.randint(10, 59)}:{random.randint(10, 59)}",
            level=random.choice(levels), msg=random.choice(msgs)))


# ========== 模型效果评估 ==========
def seed_evaluation(db):
    et = ["实体识别", "关系抽取", "OCR 识别", "事件构建"]
    for i in range(18):
        db.add(EvalTask(
            model=f"{random.choice(et)}-v{random.randint(1, 6)}.{random.randint(0, 9)}",
            modelType=random.choice(et), dataset=f"测试集-2026{str(i + 1).zfill(3)}",
            f1=rf(0.85, 0.97, 3), precision=rf(0.86, 0.98, 3), recall=rf(0.83, 0.96, 3),
            status=random.choice(["已完成", "评估中"]),
            evalAt=f"2026-06-0{random.randint(1, 9)} 1{random.randint(0, 5)}:20"))
    for i in range(12):
        db.add(EvalReport(
            name=f"模型评估报告-{random.choice(['实体识别', 'OCR', '关系抽取'])}-v{random.randint(1, 6)}.{random.randint(0, 9)}",
            model=f"model-v{random.randint(1, 6)}.{random.randint(0, 9)}", f1=rf(0.85, 0.97, 3),
            conclusion=random.choice(["建议上线", "建议优化后上线", "不建议上线"]),
            creator=random.choice(["张三", "李四"]), createdAt=f"2026-06-0{random.randint(1, 9)}",
            status=random.choice(["已生成", "待审批", "已审批"])))
    contents = [
        "2026年3月，犯罪嫌疑人李某在朝阳区某银行转账50万元至王某账户",
        "经讯问，张某对盗窃东城区某商铺财物的事实供认不讳",
        "涉案账户 6217**** 于2月15日发生多笔异常大额交易",
    ]
    outputs = ["实体: [李某/人名, 朝阳区/地点, 50万元/金额]", "事件: 盗窃(时间, 地点, 嫌疑人)", "关系: (李某, 转账, 王某)"]
    for i in range(20):
        db.add(ReviewSample(
            content=random.choice(contents), modelOutput=random.choice(outputs),
            reviewer=random.choice(["办案民警-赵", "标注员-钱", "办案民警-孙"]),
            result=random.choice(["正确", "正确", "正确", "错误", "待复核"]),
            reviewedAt=f"2026-06-0{random.randint(1, 9)}"))
    types = ["实体边界错误", "类型误判", "漏识别", "关系抽取错误", "事件要素缺失"]
    for i in range(25):
        db.add(ErrorCase(
            errorType=random.choice(types), content="犯罪嫌疑人在2026年初多次往返于江浙沪一带",
            expected="时间: 2026年初", actual="时间: 2026年",
            modelType=random.choice(["实体识别", "关系抽取", "事件构建"]), count=random.randint(1, 30)))


# ========== 评估聚合分析（自动化指标 / 各类别 / 基准对比 / 场景验证）==========
# 迁自原 crud 硬编码常量，落库后可维护、随模型增删；二期评估引擎写入同一批表。
_EVAL_METRICS = {
    "ocr": [("字符准确率", 98.6, "%"), ("行准确率", 95.2, "%"), ("平均编辑距离", 0.04, ""), ("推理耗时", 42, "ms")],
    "ner": [("精确率", 94.8, "%"), ("召回率", 92.3, "%"), ("F1 值", 93.5, "%"), ("实体类型数", 12, "类")],
    "relation": [("三元组准确率", 89.7, "%"), ("关系召回率", 87.1, "%"), ("F1 值", 88.4, "%"), ("关系类型数", 8, "类")],
    "event": [("事件识别准确率", 91.2, "%"), ("要素抽取 F1", 88.9, "%"), ("触发词准确率", 90.5, "%"), ("事件类型数", 6, "类")],
}
_EVAL_PER_CLASS = [
    ("人名", 96.2, 95.1, 95.6), ("组织机构", 93.4, 91.0, 92.2), ("时间", 97.8, 96.5, 97.1),
    ("地点", 92.1, 89.7, 90.9), ("金额", 95.5, 94.2, 94.8), ("案由", 86.3, 82.5, 84.4),
]
_BENCHMARK = [
    ("精确率", 94.8, 91.2, 93.0), ("召回率", 92.3, 88.5, 90.1), ("F1 值", 93.5, 89.8, 91.5),
    ("推理速度", 88, 90, 85), ("鲁棒性", 90, 85, 88),
]
_SCENE_CASES = [
    ("（2026）刑侦字第 218 号", "盗窃", 120, 94.2, False),
    ("（2026）刑侦字第 365 号", "诈骗", 86, 91.5, True),
    ("（2026）刑侦字第 142 号", "涉毒", 64, 88.7, True),
    ("（2026）刑侦字第 507 号", "经济犯罪", 158, 95.6, False),
    ("（2026）刑侦字第 233 号", "盗窃", 102, 93.1, False),
    ("（2026）刑侦字第 419 号", "诈骗", 75, 86.4, True),
    ("（2026）刑侦字第 188 号", "经济犯罪", 140, 96.0, False),
    ("（2026）刑侦字第 321 号", "涉毒", 58, 89.3, True),
    ("（2026）刑侦字第 276 号", "盗窃", 110, 92.8, False),
    ("（2026）刑侦字第 460 号", "经济犯罪", 132, 94.9, False),
]


def seed_eval_aggregates(db):
    """灌入评估聚合分析数据（自动化指标 / 各类别 / 基准对比 / 场景案件）。"""
    for mtype, items in _EVAL_METRICS.items():
        for i, (name, val, unit) in enumerate(items):
            db.add(EvalMetric(modelType=mtype, name=name, value=val, unit=unit, seq=i))
        # 各类别细分指标：四种模型类型共用同一套类别（与原行为一致）
        for i, (label, p, r, f) in enumerate(_EVAL_PER_CLASS):
            db.add(EvalPerClass(modelType=mtype, label=label, precision=p, recall=r, f1=f, seq=i))
    for i, (dim, cur, prod, hist) in enumerate(_BENCHMARK):
        db.add(BenchmarkResult(dim=dim, current=cur, prod=prod, hist=hist, seq=i))
    for caseNo, ctype, cnt, acc, hard in _SCENE_CASES:
        db.add(SceneCase(caseNo=caseNo, type=ctype, sampleCount=cnt, accuracy=acc, hard=hard))


def ensure_eval_aggregates():
    """幂等灌入评估聚合数据：表为空才写。每次启动调用，兼容既有库（新增表自动补数据）。"""
    db = SessionLocal()
    try:
        if db.query(EvalMetric).count() == 0:
            seed_eval_aggregates(db)
            db.commit()
            print("评估聚合数据已灌入（eval_metric / eval_per_class / benchmark_result / scene_case）")
    finally:
        db.close()


def seed_convert_rules(db):
    """灌入内置的 5 条默认转换规则（与代码内 DEFAULT_RULES 等价）。

    需在 dataset_type 已灌入后调用：据 datasetTypeValue 解析出 dataset_type_id（方案2 FK）。
    """
    from app.services.dataset_convert import DEFAULT_RULES
    type_id = {t.value: t.id for t in db.query(DatasetType).all()}
    for r in DEFAULT_RULES:
        db.add(ConvertRule(
            datasetTypeId=type_id.get(r["datasetTypeValue"]),
            typeMatch=r["typeMatch"], name=r["name"], priority=r["priority"],
            instruction=r["instruction"], inputAliases=r["inputAliases"],
            outputAliases=r["outputAliases"], outputFormat=r["outputFormat"], enabled=r["enabled"],
        ))


def ensure_convert_rules():
    """幂等灌入数据转换规则：表为空才写。每次启动调用，兼容既有库。

    引擎 load_rules 在表空时也会回退内置默认，故此处仅为「让规则可在页面被看到/编辑」。
    """
    db = SessionLocal()
    try:
        if db.query(ConvertRule).count() == 0:
            seed_convert_rules(db)
            db.commit()
            print("数据转换规则已灌入（convert_rule，5 条默认规则）")
    finally:
        db.close()


# 数据集类型字典（value 与前端 dict.js DATA_TYPES 一致，label 即写入 dataset.type 的值）
DATASET_TYPE_DICT = [
    ("ocr", "OCR 校对结果"),
    ("entity", "实体关系标注"),
    ("event", "事件标注"),
    ("risk", "风险样本"),
    ("path", "路径分析"),
]


def seed_dataset_types(db):
    for i, (value, label) in enumerate(DATASET_TYPE_DICT):
        db.add(DatasetType(value=value, label=label, seq=i, enabled=True))


def ensure_dataset_types():
    """幂等灌入数据集类型字典：表为空才写。每次启动调用，兼容既有库。"""
    db = SessionLocal()
    try:
        if db.query(DatasetType).count() == 0:
            seed_dataset_types(db)
            db.commit()
            print("数据集类型字典已灌入（dataset_type，4 条）")
    finally:
        db.close()


def ensure_convert_rule_links():
    """方案2 迁移补链：把 datasetTypeId 为空的旧规则，按其 typeMatch 关键字关联到 dataset_type。

    幂等：只处理未关联的规则。兼容「先前已灌规则、后加 dataset_type_id 列」的既有库。
    需在 dataset_type 已灌入后调用。
    """
    db = SessionLocal()
    try:
        types = db.query(DatasetType).all()
        unlinked = db.query(ConvertRule).filter(ConvertRule.datasetTypeId.is_(None)).all()
        if not types or not unlinked:
            return
        fixed = 0
        for r in unlinked:
            kws = [k.strip().lower() for k in (r.typeMatch or "").replace("，", ",").split(",") if k.strip()]
            match = None
            for t in types:
                hay = f"{t.value or ''} {t.label or ''}".lower()
                if any(k in hay for k in kws):
                    match = t
                    break
            if match:
                r.datasetTypeId = match.id
                fixed += 1
        if fixed:
            db.commit()
            print(f"转换规则补链完成（按 typeMatch 关联到 dataset_type）：{fixed} 条")
    finally:
        db.close()


def ensure_path_pipeline():
    """幂等补齐「路径分析」数据集类型 + 其转换规则。

    既有库已灌过 4 类型/5 规则，ensure_dataset_types/ensure_convert_rules 仅在表空时写，
    不会再补这一类；故单独幂等补齐，让 路径分析 在导入下拉/转换规则页可见、可走完整流水线。
    需在 dataset_type 已存在后调用。
    """
    db = SessionLocal()
    try:
        t = db.query(DatasetType).filter(DatasetType.value == "path").first()
        if not t:
            seqs = [x.seq or 0 for x in db.query(DatasetType).all()]
            t = DatasetType(value="path", label="路径分析", seq=(max(seqs) + 1 if seqs else 0), enabled=True)
            db.add(t)
            db.commit()
            db.refresh(t)
            print("数据集类型补齐：路径分析（path）")
        has_rule = db.query(ConvertRule).filter(ConvertRule.datasetTypeId == t.id).first()
        if not has_rule:
            from app.services.dataset_convert import DEFAULT_RULES
            r = next((x for x in DEFAULT_RULES if x["datasetTypeValue"] == "path"), None)
            if r:
                db.add(ConvertRule(
                    datasetTypeId=t.id, typeMatch=r["typeMatch"], name=r["name"], priority=r["priority"],
                    instruction=r["instruction"], inputAliases=r["inputAliases"],
                    outputAliases=r["outputAliases"], outputFormat=r["outputFormat"], enabled=r["enabled"],
                ))
                db.commit()
                print("转换规则补齐：路径还原研判")
    finally:
        db.close()


def ensure_dataset_stage():
    """流水线 P1 回填：旧数据集 stage 为空时按 desensitized/status 推断；旧脱敏规则补 maskType。

    幂等：只处理为空的字段。兼容「先前已有数据、后加列」的既有库。
    """
    db = SessionLocal()
    try:
        changed = 0
        for ds in db.query(Dataset).filter(Dataset.stage.is_(None)).all():
            if ds.status == "已归档":
                ds.stage = "已归档"
            elif ds.desensitized:
                ds.stage = "已脱敏"
            elif ds.status == "已完成":
                ds.stage = "已发布"
            else:
                ds.stage = "待标注"
            changed += 1
        # 旧脱敏规则按字段名补 maskType
        kw = [("身份证", "idcard"), ("手机", "phone"), ("银行卡", "bankcard"),
              ("姓名", "name"), ("邮箱", "email"), ("email", "email")]
        for r in db.query(DesensitizeRule).filter(DesensitizeRule.maskType.is_(None)).all():
            f = (r.field or "").lower()
            r.maskType = next((mt for k, mt in kw if k.lower() in f), "custom")
            changed += 1
        if changed:
            db.commit()
            print(f"数据集流水线回填完成（stage / maskType）：{changed} 处")
    finally:
        db.close()


# ========== 模型版本管理 ==========
MV_STATUS = ["evaluating", "evaluated", "gray", "online", "offline", "archived"]
MV_TYPES = ["OCR 识别", "实体识别", "关系抽取", "事件构建", "风险预警"]


def seed_model(db):
    for i in range(30):
        db.add(ModelVersion(
            name=f"{random.choice(MV_TYPES)}模型", version=f"v{random.randint(1, 6)}.{random.randint(0, 9)}",
            modelType=random.choice(MV_TYPES), dataset=f"数据集-2026{str(i + 1).zfill(3)}",
            f1=rf(0.85, 0.97, 3), size=f"{rf(0.5, 14, 1)} GB", status=random.choice(MV_STATUS),
            trainAt=f"2026-0{random.randint(1, 6)}-{random.randint(10, 28)} 1{random.randint(0, 5)}:00",
            creator=random.choice(["张三", "李四", "王五"])))
    db.add(GrayRelease(name="实体识别模型 v5.2", scope="刑侦支队 / 朝阳分局", traffic=20,
                       requests=12480, errorRate=0.8, accuracy=93.6, status="灰度中", startAt="2026-06-06 10:00"))
    db.add(GrayRelease(name="OCR 识别模型 v3.4", scope="指定案件（专案 2026-018）", traffic=10,
                       requests=3260, errorRate=1.2, accuracy=97.8, status="灰度中", startAt="2026-06-07 09:30"))
    rh = [
        ("v5.2", "全量上线", "审批管理员-王", "2026-06-08 15:00", "成功", "灰度验证 F1 93.5%，达标"),
        ("v5.1", "灰度上线", "算法工程师-张", "2026-06-06 10:00", "成功", "20% 流量"),
        ("v5.0", "回滚", "系统管理员-李", "2026-05-30 22:10", "成功", "线上误识别率升高，回滚至 v4.9"),
        ("v4.9", "全量上线", "审批管理员-王", "2026-05-20 14:00", "成功", ""),
    ]
    for r in rh:
        db.add(ReleaseHistory(version=r[0], action=r[1], operator=r[2], time=r[3], status=r[4], note=r[5]))
    dt = [
        ("本地推理服务器集群", "本地", "8 × A100", "在线", 42),
        ("昇腾 NPU 集群", "NPU", "16 × 昇腾910B", "在线", 67),
        ("政务云推理节点", "云环境", "弹性 GPU", "在线", 28),
        ("边缘部署节点（分局）", "边缘", "4 × T4", "离线", 0),
    ]
    for d in dt:
        db.add(DeployTarget(name=d[0], type=d[1], spec=d[2], status=d[3], load=d[4]))


# ========== 微调配置管理 ==========
def seed_config(db):
    bm = [
        ("Qwen2-7B", "开源", "阿里通义", "7B", "Apache-2.0", 32, "2026-03-10", True),
        ("Qwen2-72B", "开源", "阿里通义", "72B", "Apache-2.0", 8, "2026-03-10", True),
        ("Llama3-8B", "开源", "Meta", "8B", "Llama-3", 15, "2026-02-22", True),
        ("GLM4-9B", "开源", "智谱", "9B", "GLM-License", 11, "2026-04-01", True),
        ("公安基座模型 v3", "原生", "内部研发", "13B", "内部授权", 46, "2026-01-15", True),
        ("第三方风控预训练模型", "第三方", "某安全厂商", "6B", "商业授权", 4, "2026-05-12", False),
    ]
    for m in bm:
        db.add(BaseModelInfo(name=m[0], source=m[1], vendor=m[2], params=m[3],
                             license=m[4], useCount=m[5], addedAt=m[6], enabled=m[7]))
    ht = [
        ("审讯笔录实体识别模板", "实体识别", "2e-5", 16, 8, "AdamW", 18),
        ("资金流关系抽取模板", "关系抽取", "3e-5", 8, 10, "AdamW", 9),
        ("OCR 校对微调模板", "OCR 识别", "1e-4", 32, 5, "Adam", 22),
        ("风险预警分类模板", "风险预警", "2e-5", 16, 6, "AdamW", 7),
    ]
    for t in ht:
        db.add(HyperTemplate(name=t[0], scene=t[1], lr=t[2], batchSize=t[3], epochs=t[4], optimizer=t[5], useCount=t[6]))
    db.add(ClusterInfo(totalGpu=32, usedGpu=21, totalCpu=512, usedCpu=280, runningTasks=6, queuedTasks=4))
    quotas = [
        ("刑侦支队", 12, 8, 48, 4), ("经侦支队", 8, 5, 24, 3),
        ("网安支队", 6, 4, 24, 2), ("情报中心", 6, 4, 36, 2),
    ]
    for q in quotas:
        db.add(ResourceQuota(dept=q[0], gpuQuota=q[1], gpuUsed=q[2], maxDuration=q[3], maxConcurrent=q[4]))
    db.add(AutoTuneConfig(
        enabled=True, objective="maximize_f1", searchAlgo="bayesian", maxTrials=30, parallelTrials=4,
        searchSpace=[
            {"param": "学习率 (lr)", "range": "1e-5 ~ 1e-3", "type": "log"},
            {"param": "批次大小 (batch_size)", "range": "8, 16, 32, 64", "type": "choice"},
            {"param": "训练轮数 (epochs)", "range": "3 ~ 12", "type": "int"},
            {"param": "warmup 比例", "range": "0.0 ~ 0.1", "type": "float"},
        ]))
    for i in range(8):
        db.add(AutoTuneTrial(
            trial=i + 1, lr=["2e-5", "3e-5", "5e-5", "1e-4"][i % 4], batchSize=[16, 32, 8, 16][i % 4],
            epochs=random.randint(5, 10), f1=round(0.88 + random.random() * 0.08, 3),
            status="已完成" if i < 6 else "运行中"))
    perms = ["创建微调任务", "配置超参数", "审批模型上线", "模型回滚", "数据集导出", "资源配额管理", "权限分配"]
    for p in perms:
        db.add(PermCatalog(name=p))
    roles = [
        ("普通用户", ["创建微调任务"]),
        ("标注人员", ["创建微调任务"]),
        ("算法工程师", ["创建微调任务", "配置超参数", "数据集导出"]),
        ("审批管理员", ["创建微调任务", "审批模型上线", "模型回滚"]),
        ("系统管理员", perms),
    ]
    for r in roles:
        db.add(SysRole(role=r[0], granted=r[1]))


# ========== 操作日志 ==========
def seed_oplog(db):
    samples = [
        ("admin", "系统管理员", "系统", "登录", "POST", "/api/auth/login", "成功", "登录成功"),
        ("analyst", "张三", "微调任务", "创建微调任务", "POST", "/api/task", "成功", ""),
        ("analyst", "张三", "微调任务", "变更任务状态", "PUT", "/api/task/3/status", "成功", ""),
        ("approver", "王五", "模型版本", "变更模型状态", "PUT", "/api/model/5/status", "成功", ""),
        ("approver", "王五", "微调配置", "保存角色权限", "POST", "/api/config/role-permissions", "成功", ""),
        ("labeler", "李四", "数据集管理", "创建数据集", "POST", "/api/dataset", "成功", ""),
        ("analyst", "张三", "微调配置", "保存超参模板", "POST", "/api/config/hyper-templates", "成功", ""),
        ("unknown", "-", "系统", "登录", "POST", "/api/auth/login", "失败", "用户名或密码错误"),
        ("admin", "系统管理员", "微调配置", "保存基础模型", "POST", "/api/config/base-models", "成功", ""),
        ("admin", "系统管理员", "系统", "退出登录", "POST", "/api/auth/logout", "成功", ""),
    ]
    for i, s in enumerate(samples):
        db.add(OperationLog(
            username=s[0], realName=s[1], module=s[2], action=s[3], method=s[4],
            path=s[5], ip=f"10.20.{random.randint(1, 9)}.{random.randint(2, 254)}",
            status=s[6], detail=s[7],
            time=f"2026-06-0{random.randint(1, 9)} 1{random.randint(0, 5)}:{random.randint(10, 59)}:{random.randint(10, 59)}"))


# ========== 用户 ==========
# (用户名, 密码, 姓名, 部门, 角色)
DEFAULT_USERS = [
    ("admin", "admin123", "系统管理员", "信息技术处", "系统管理员"),
    ("analyst", "123456", "张三", "刑侦支队 · 技术大队", "算法工程师"),
    ("approver", "123456", "王五", "审批办公室", "审批管理员"),
    ("labeler", "123456", "李四", "情报中心", "标注人员"),
]


def ensure_users():
    """幂等创建默认用户（已存在则跳过）。每次启动调用，保证 sys_user 有账号。"""
    db = SessionLocal()
    try:
        created = 0
        for username, pw, name, dept, role in DEFAULT_USERS:
            if not db.query(User).filter(User.username == username).first():
                db.add(User(username=username, password_hash=hash_password(pw),
                            real_name=name, dept=dept, role=role, status="active"))
                created += 1
        db.commit()
        if created:
            print(f"默认用户创建完成：{created} 个")
    finally:
        db.close()


# ========== 入口 ==========
def run_seed():
    db = SessionLocal()
    try:
        n = seed_dataset(db)
        seed_task(db)
        seed_evaluation(db)
        seed_eval_aggregates(db)
        seed_model(db)
        seed_config(db)
        seed_dataset_types(db)   # 须在 convert_rules 之前：规则按类型 value 解析 FK
        seed_convert_rules(db)
        seed_oplog(db)
        db.commit()
        print(f"种子数据写入完成（全部模块），datasets={n}")
    finally:
        db.close()
    ensure_users()
    ensure_path_pipeline()   # 补齐「路径分析」类型+规则（DATASET_TYPE_DICT 已含，但显式幂等保证）


def seed_if_empty():
    db = SessionLocal()
    try:
        count = db.query(Dataset).count()
    finally:
        db.close()
    if count == 0:
        run_seed()
    else:
        print(f"已存在 {count} 条数据集，跳过种子。")


if __name__ == "__main__":
    init_db()
    run_seed()
