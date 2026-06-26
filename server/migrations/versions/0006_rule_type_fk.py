"""convert_rule.dataset_type_id: 方案2 规则归属数据集类型的外键列

幂等：用 inspector 判列存在再加，兼容全新库（基线 create_all 已建）与既有库、
MySQL 与 SQLite。数据补链由 scripts.seed.ensure_convert_rule_links 启动时幂等完成
（按旧 typeMatch 关键字关联到 dataset_type），故此处仅加列、不做数据迁移。

Revision ID: 0006_rule_type_fk
Revises: 0005_dataset_type
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_rule_type_fk"
down_revision: Union[str, None] = "0005_dataset_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("convert_rule"):
        cols = {c["name"] for c in insp.get_columns("convert_rule")}
        if "dataset_type_id" not in cols:
            op.add_column("convert_rule", sa.Column("dataset_type_id", sa.Integer(), nullable=True))
            op.create_index("ix_convert_rule_dataset_type_id", "convert_rule", ["dataset_type_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("convert_rule"):
        cols = {c["name"] for c in insp.get_columns("convert_rule")}
        if "dataset_type_id" in cols:
            op.drop_index("ix_convert_rule_dataset_type_id", table_name="convert_rule")
            op.drop_column("convert_rule", "dataset_type_id")
