"""eval aggregates: 自动化指标 / 各类别 / 基准对比 / 场景验证 落库四表

幂等：用 inspector 判表存在再建，兼容全新库（基线 create_all 已建）与既有库、
MySQL 与 SQLite。数据由 scripts.seed.ensure_eval_aggregates 启动时幂等灌入。

Revision ID: 0003_eval_aggregates
Revises: 0002_real_engine
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_eval_aggregates"
down_revision: Union[str, None] = "0002_real_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("eval_metric"):
        op.create_table(
            "eval_metric",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("model_type", sa.String(32), index=True),
            sa.Column("name", sa.String(32)),
            sa.Column("value", sa.Float()),
            sa.Column("unit", sa.String(16)),
            sa.Column("seq", sa.Integer()),
        )
    if not insp.has_table("eval_per_class"):
        op.create_table(
            "eval_per_class",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("model_type", sa.String(32), index=True),
            sa.Column("label", sa.String(32)),
            sa.Column("precision_val", sa.Float()),
            sa.Column("recall", sa.Float()),
            sa.Column("f1", sa.Float()),
            sa.Column("seq", sa.Integer()),
        )
    if not insp.has_table("benchmark_result"):
        op.create_table(
            "benchmark_result",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("dim", sa.String(32)),
            sa.Column("current_val", sa.Float()),
            sa.Column("prod_val", sa.Float()),
            sa.Column("hist_val", sa.Float()),
            sa.Column("seq", sa.Integer()),
        )
    if not insp.has_table("scene_case"):
        op.create_table(
            "scene_case",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("case_no", sa.String(64)),
            sa.Column("type", sa.String(32)),
            sa.Column("sample_count", sa.Integer()),
            sa.Column("accuracy", sa.Float()),
            sa.Column("hard", sa.Boolean()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for table in ("scene_case", "benchmark_result", "eval_per_class", "eval_metric"):
        if insp.has_table(table):
            op.drop_table(table)
