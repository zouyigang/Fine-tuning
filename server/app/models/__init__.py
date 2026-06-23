"""集中导入所有 ORM 模型，确保 Base.metadata 完整（建表时需要）。"""
from app.models.user import User  # noqa: F401
from app.models.dataset import (  # noqa: F401
    Dataset,
    DatasetVersion,
    DesensitizeRule,
    AnnotationTask,
    DatasetPermission,
)
from app.models.task import (  # noqa: F401
    TrainTask,
    TrainMetric,
    TrainLog,
    TaskArtifact,
    ScheduleItem,
)
from app.models.evaluation import (  # noqa: F401
    EvalTask,
    EvalReport,
    ReviewSample,
    ErrorCase,
)
from app.models.model_version import (  # noqa: F401
    ModelVersion,
    GrayRelease,
    ReleaseHistory,
    DeployTarget,
)
from app.models.config import (  # noqa: F401
    BaseModelInfo,
    HyperTemplate,
    ResourceQuota,
    ClusterInfo,
    AutoTuneConfig,
    AutoTuneTrial,
    SysRole,
    PermCatalog,
)
from app.models.oplog import OperationLog  # noqa: F401
