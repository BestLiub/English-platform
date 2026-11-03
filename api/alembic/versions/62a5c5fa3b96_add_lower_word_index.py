"""add lower word index

Revision ID: 62a5c5fa3b96
Revises: d9fba54afb37
Create Date: 2026-11-02 15:45:22.919542
"""
from typing import Sequence, Union

from alembic import op

revision: str = '62a5c5fa3b96'
down_revision: Union[str, None] = 'd9fba54afb37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 这两条索引 SQLAlchemy 在 SQLite 上反射不了（表达式索引、以及早先由导入脚本建的
    # ix_word_frq），autogenerate 既看不见也生成不出来，所以手写并用 IF NOT EXISTS 保证幂等：
    # 老库已经有了就跳过，新库照常创建。
    op.execute("CREATE INDEX IF NOT EXISTS ix_word_frq ON word (frq)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_word_lower ON word (lower(word))")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_word_lower")
