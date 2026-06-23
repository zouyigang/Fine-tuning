"""real engine: train_task 加超参/运行列 + model_version.task_id + task_artifact 表

幂等：基线用 create_all，全新库的 train_task/model_version 已含这些列、task_artifact
已建，故此处先用 inspector 判存在再加/建，兼容全新库与既有库、MySQL 与 SQLite。

Revision ID: 0002_real_engine
Revises: 0001_baseline
Create Date: 2026-06-23
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_real_engine"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# 待补列：表 -> [(列名, 类型)]
_NEW_COLUMNS = {
    "train_task": [
        ("method", sa.String(16)),
        ("hyperparams", sa.JSON()),
        ("base_model_path", sa.String(255)),
        ("output_dir", sa.String(255)),
        ("pid", sa.Integer()),
        ("error_msg", sa.String(512)),
        ("model_version_id", sa.Integer()),
        ("finished_at", sa.String(32)),
    ],
    "model_version": [
        ("task_id", sa.Integer()),
    ],
}


def _existing_cols(insp, table: str) -> set:
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table, cols in _NEW_COLUMNS.items():
        have = _existing_cols(insp, table)
        if not have:  # 表不存在（理论不会，基线已建），跳过
            continue
        for name, type_ in cols:
            if name not in have:
                op.add_column(table, sa.Column(name, type_, nullable=True))

    if not insp.has_table("task_artifact"):
        op.create_table(
            "task_artifact",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("task_id", sa.Integer(), index=True),
            sa.Column("kind", sa.String(16)),
            sa.Column("path", sa.String(255)),
            sa.Column("size", sa.String(16)),
            sa.Column("created_at", sa.String(32)),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("task_artifact"):
        op.drop_table("task_artifact")
    for table, cols in _NEW_COLUMNS.items():
        have = _existing_cols(insp, table)
        for name, _ in cols:
            if name in have:
                op.drop_column(table, name)
