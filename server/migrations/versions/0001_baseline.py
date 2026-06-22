"""baseline: 全量建表（以当前 ORM 模型为基线）

本项目此前用 SQLAlchemy create_all 自动建表，引入 Alembic 后以本迁移作为基线：
- 全新库：alembic upgrade head 会按当前模型创建全部表（含新增的
  dataset_file / model_export / model_deployment / schedule_item）。
- 既有库（已 create_all 过）：create_all 带 checkfirst，仅补建缺失的新表，
  随后写入 alembic_version 完成基线标记；或用 `alembic stamp head` 直接标记。

后续 schema 变更请用 `alembic revision --autogenerate -m "xxx"` 生成增量迁移。

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-22
"""
from typing import Sequence, Union

from alembic import op

from app.core.database import Base
import app.models  # noqa: F401 注册全部模型

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # checkfirst=True：仅创建尚不存在的表，对既有库安全
    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
