"""dataset_type: 数据集类型字典表（导入页类型下拉数据源，可启停/排序）

幂等：用 inspector 判表存在再建，兼容全新库（基线 create_all 已建）与既有库、
MySQL 与 SQLite。默认 4 条由 scripts.seed.ensure_dataset_types 启动时幂等灌入。

Revision ID: 0005_dataset_type
Revises: 0004_convert_rule
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_dataset_type"
down_revision: Union[str, None] = "0004_convert_rule"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("dataset_type"):
        op.create_table(
            "dataset_type",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("value", sa.String(32), unique=True),
            sa.Column("label", sa.String(64)),
            sa.Column("seq", sa.Integer()),
            sa.Column("enabled", sa.Boolean()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("dataset_type"):
        op.drop_table("dataset_type")
