"""train_task 增 started_at 列：训练真实开始时间（引擎 _launch 子进程起来时落库）

幂等：inspector 判列存在再加。配合 created_at(入队)/finished_at(收尾) 计算「已耗时」——
列表 duration 由 started_at→finished_at(或 now) 实时算，不再用创建时写死的占位值。

Revision ID: 0012_task_started_at
Revises: 0011_desensitize_replacement
Create Date: 2026-06-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012_task_started_at"
down_revision: Union[str, None] = "0011_desensitize_replacement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("train_task"):
        cols = {c["name"] for c in insp.get_columns("train_task")}
        if "started_at" not in cols:
            op.add_column("train_task", sa.Column("started_at", sa.String(32), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("train_task"):
        cols = {c["name"] for c in insp.get_columns("train_task")}
        if "started_at" in cols:
            op.drop_column("train_task", "started_at")
