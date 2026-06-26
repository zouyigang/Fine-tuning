"""convert_rule: 数据集 → alpaca 指令样本的转换规则表（页面可维护）

幂等：用 inspector 判表存在再建，兼容全新库（基线 create_all 已建）与既有库、
MySQL 与 SQLite。默认 5 条规则由 scripts.seed.ensure_convert_rules 启动时幂等灌入。

Revision ID: 0004_convert_rule
Revises: 0003_eval_aggregates
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_convert_rule"
down_revision: Union[str, None] = "0003_eval_aggregates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table("convert_rule"):
        op.create_table(
            "convert_rule",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("type_match", sa.String(128)),
            sa.Column("name", sa.String(64)),
            sa.Column("priority", sa.Integer()),
            sa.Column("instruction", sa.Text()),
            sa.Column("input_aliases", sa.JSON()),
            sa.Column("output_aliases", sa.JSON()),
            sa.Column("output_format", sa.String(16)),
            sa.Column("enabled", sa.Boolean()),
            sa.Column("created_at", sa.DateTime()),
            sa.Column("updated_at", sa.DateTime()),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("convert_rule"):
        op.drop_table("convert_rule")
