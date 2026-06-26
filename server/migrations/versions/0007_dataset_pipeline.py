"""数据集流水线 P1：dataset.stage + desensitize_rule.mask_type/pattern

幂等：用 inspector 判列存在再加，兼容全新库（基线 create_all 已建）与既有库、
MySQL 与 SQLite。旧数据 stage 由 scripts.seed.ensure_dataset_stage 启动时按
desensitized/status 幂等回填。

Revision ID: 0007_dataset_pipeline
Revises: 0006_rule_type_fk
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_dataset_pipeline"
down_revision: Union[str, None] = "0006_rule_type_fk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cols(insp, table):
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("dataset"):
        if "stage" not in _cols(insp, "dataset"):
            op.add_column("dataset", sa.Column("stage", sa.String(16), nullable=True))
    if insp.has_table("desensitize_rule"):
        cols = _cols(insp, "desensitize_rule")
        if "mask_type" not in cols:
            op.add_column("desensitize_rule", sa.Column("mask_type", sa.String(16), nullable=True))
        if "pattern" not in cols:
            op.add_column("desensitize_rule", sa.Column("pattern", sa.String(255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("desensitize_rule"):
        cols = _cols(insp, "desensitize_rule")
        if "pattern" in cols:
            op.drop_column("desensitize_rule", "pattern")
        if "mask_type" in cols:
            op.drop_column("desensitize_rule", "mask_type")
    if insp.has_table("dataset") and "stage" in _cols(insp, "dataset"):
        op.drop_column("dataset", "stage")
