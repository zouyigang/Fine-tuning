"""dataset_file 增 split 列：发布时按比例切分训练/验证/测试集

幂等：inspector 判列存在再加。'train'=训练集 / 'val'=验证集 / 'test'=测试集 /
None=未切分（旧数据，整份）。训练读 train(+val)，评估引擎读 test。

Revision ID: 0010_dataset_file_split
Revises: 0009_dataset_file_variant
Create Date: 2026-06-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010_dataset_file_split"
down_revision: Union[str, None] = "0009_dataset_file_variant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("dataset_file"):
        cols = {c["name"] for c in insp.get_columns("dataset_file")}
        if "split" not in cols:
            op.add_column("dataset_file", sa.Column("split", sa.String(8), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("dataset_file"):
        cols = {c["name"] for c in insp.get_columns("dataset_file")}
        if "split" in cols:
            op.drop_column("dataset_file", "split")
