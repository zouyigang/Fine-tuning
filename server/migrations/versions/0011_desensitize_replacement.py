"""desensitize_rule 增 replacement 列：脱敏替换串（re.sub 模板，支持 \\1\\2 反向引用）

幂等：inspector 判列存在再加。模式型(idcard/phone/bankcard/email)与 custom 通用；
留空时模式型回退内置默认、custom 用 ***。配合 ensure_desensitize_patterns 回填内置正则/替换串。

Revision ID: 0011_desensitize_replacement
Revises: 0010_dataset_file_split
Create Date: 2026-06-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011_desensitize_replacement"
down_revision: Union[str, None] = "0010_dataset_file_split"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("desensitize_rule"):
        cols = {c["name"] for c in insp.get_columns("desensitize_rule")}
        if "replacement" not in cols:
            op.add_column("desensitize_rule", sa.Column("replacement", sa.String(255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if insp.has_table("desensitize_rule"):
        cols = {c["name"] for c in insp.get_columns("desensitize_rule")}
        if "replacement" in cols:
            op.drop_column("desensitize_rule", "replacement")
