"""数据集模块出入参 Schema（Pydantic v2）。字段与前端保持一致。"""
from pydantic import BaseModel, ConfigDict, Field


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str | None = None
    dept: str | None = None
    total: int | None = 0
    labeled: int | None = 0
    progress: int | None = 0
    version: str | None = None
    desensitized: bool | None = False
    status: str | None = None
    stage: str | None = None
    owner: str | None = None
    updatedAt: str | None = None


class DatasetCreate(BaseModel):
    name: str
    type: str
    dept: str
    total: int | None = 0
    desensitized: bool | None = True
    owner: str | None = "张三"
    updatedAt: str | None = None
    fileId: int | None = None  # 关联已上传文件（本地上传方式）


class UploadOut(BaseModel):
    """文件上传返回：前端据此带 fileId + total 调用 createDataset。"""
    fileId: int
    fileName: str
    size: int
    sizeText: str
    rows: int


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: str
    desc: str | None = None
    author: str | None = None
    count: int | None = 0
    current: bool | None = False
    time: str | None = None


class VersionCreateIn(BaseModel):
    datasetId: int
    desc: str | None = None
    version: str | None = None  # 不传则自动顺延版本号


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    field: str
    rule: str
    sample: str
    enabled: bool
    maskType: str | None = "custom"
    pattern: str | None = None


class AnnotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    datasetId: int | None = Field(default=None, validation_alias="dataset_id")
    title: str
    type: str | None = None
    total: int | None = 0
    done: int | None = 0
    annotators: int | None = 0
    status: str | None = None
    deadline: str | None = None


class PermissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    secret: str | None = None
    dept: str | None = None
    roles: list[str] | None = None
    canView: bool | None = True
    canEdit: bool | None = False
    canExport: bool | None = False


class PermissionSaveItem(BaseModel):
    id: int
    roles: list[str] | None = None
    canView: bool | None = True
    canEdit: bool | None = False
    canExport: bool | None = False


class PermissionSaveIn(BaseModel):
    items: list[PermissionSaveItem] = []


class RuleCreateIn(BaseModel):
    field: str
    rule: str | None = "自定义掩码"
    sample: str | None = "****"
    enabled: bool | None = True
    maskType: str | None = "custom"   # idcard/phone/bankcard/name/email/custom
    pattern: str | None = None        # custom 时的正则


class RuleToggleIn(BaseModel):
    enabled: bool


class DesensitizeRunIn(BaseModel):
    datasetId: int


class DesensitizePreviewIn(BaseModel):
    text: str | None = ""


class AnnotationProgressIn(BaseModel):
    done: int


class AnnotationReviewIn(BaseModel):
    approved: bool


class DatasetTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    value: str | None = None
    label: str | None = None
    seq: int | None = 0
    enabled: bool | None = True


class DatasetTypeIn(BaseModel):
    id: int | None = None
    value: str
    label: str
    seq: int | None = 0
    enabled: bool | None = True


class DatasetTypeStatusIn(BaseModel):
    enabled: bool


class SampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idx: int | None = 0
    raw: dict | None = None
    labeled: dict | None = None
    masked: dict | None = None
    status: str | None = "待标注"


class SampleLabelIn(BaseModel):
    labeled: dict
