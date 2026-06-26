"""数据集流水线 P2：dataset_sample 逐样本主干表

幂等：inspector 判表存在再建。导入时灌 raw，标注写 labeled，脱敏写 masked，
发布按 masked→labeled→raw 导出训练文件。

Revision ID: 0008_dataset_sample
Revises: 0007_dataset_pipeline
Create Date: 2026-06-25
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_dataset_sample"
down_revision: Union[str, None] = "0007_dataset_pipeline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if not insp.has_table("dataset_sample"):
        op.create_table(
            "dataset_sample",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("dataset_id", sa.Integer(), index=True),
            sa.Column("idx", sa.Integer()),
            sa.Column("raw", sa.JSON()),
            sa.Column("labeled", sa.JSON()),
            sa.Column("masked", sa.JSON()),
            sa.Column("status", sa.String(16)),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("dataset_sample"):
        op.drop_table("dataset_sample")
