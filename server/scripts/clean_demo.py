"""一次性清理演示业务数据，保留账号 / 配置 / 评估参考数据。

适用场景：想让平台只展示「真实产生」的数据（大屏、工作台、各业务页）。
配合 server/.env 设 AUTO_SEED=false，避免后端重启后重新播种演示数据。

用法（在 server/ 目录，使用 .env 指向的库——本机即 MySQL）：
    D:/anaconda3/python.exe -m scripts.clean_demo

会清空（演示业务活动数据）：
    数据集及其版本/文件/权限/标注任务、训练任务及其指标/日志/产物/调度、
    评估任务/报告/复核样本/错误案例、模型版本/灰度/上线记录/部署目标/导出/部署、操作日志。
    注意：会删除这些表的「全部」行，含此前真实引擎测试产生的行（全库干净开始）。

保留（账号 / 配置 / 评估参考）：
    sys_user / sys_role / perm_catalog、base_model / hyper_template /
    resource_quota / autotune_config / autotune_trial / cluster_info、
    desensitize_rule（脱敏规则）、eval_metric / eval_per_class /
    benchmark_result / scene_case（评估三页参考数据）。
"""
from app.core.database import SessionLocal, init_db
from app.models.dataset import (
    Dataset, DatasetVersion, DatasetFile, DatasetPermission, AnnotationTask,
)
from app.models.task import TrainTask, TrainMetric, TrainLog, TaskArtifact, ScheduleItem
from app.models.evaluation import EvalTask, EvalReport, ReviewSample, ErrorCase
from app.models.model_version import (
    ModelVersion, GrayRelease, ReleaseHistory, DeployTarget, ModelExport, ModelDeployment,
)
from app.models.oplog import OperationLog

# 待清空的演示业务表（无外键约束，逐表 delete 即可）
_CLEAR = [
    DatasetVersion, DatasetFile, DatasetPermission, AnnotationTask, Dataset,
    TrainMetric, TrainLog, TaskArtifact, ScheduleItem, TrainTask,
    EvalTask, EvalReport, ReviewSample, ErrorCase,
    GrayRelease, ReleaseHistory, DeployTarget, ModelExport, ModelDeployment, ModelVersion,
    OperationLog,
]


def clean():
    init_db()
    db = SessionLocal()
    try:
        total = 0
        for model in _CLEAR:
            n = db.query(model).delete()
            total += n
            print(f"  清空 {model.__tablename__}: -{n}")
        db.commit()
        print(f"\n演示业务数据已清理，共删除 {total} 行。")
        print("保留：账号/角色/权限、基础模型/超参/配额/调优/集群、脱敏规则、评估三页参考数据。")
        print("请确认 server/.env 已设 AUTO_SEED=false，并重启后端使更改生效。")
    finally:
        db.close()


if __name__ == "__main__":
    clean()
