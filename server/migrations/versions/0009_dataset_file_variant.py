"""dataset_file 增 variant 列：同一标注按模型子类型发布多份训练文件

幂等：inspector 判列存在再加。'ner'=命名实体训练集 / 'relation'=关系三元组训练集 /
None=单一训练文件。引擎按任务 modelType（实体识别/关系抽取）选对应文件。

Revision ID: 0009_dataset_file_variant
Revises: 0008_dataset_sample
Create Date: 2026-06-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_dataset_file_variant"
down_revision: Union[str, None] = "0008_dataset_sample"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("dataset_file"):
        cols = {c["name"] for c in insp.get_columns("dataset_file")}
        if "variant" not in cols:
            op.add_column("dataset_file", sa.Column("variant", sa.String(16), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("dataset_file"):
        cols = {c["name"] for c in insp.get_columns("dataset_file")}
        if "variant" in cols:
            op.drop_column("dataset_file", "variant")
