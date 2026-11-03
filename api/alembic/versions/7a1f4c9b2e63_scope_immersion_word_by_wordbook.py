"""scope immersion_word by wordbook

Revision ID: 7a1f4c9b2e63
Revises: d2f80fc177a2
Create Date: 2026-11-03 16:20:00.000000

沉浸进度必须按词库隔离：cet4 和 cet6 有 3451 个重叠词，用 (user_id, word_id)
做唯一键会导致重置六级清掉约九成四级的掌握记录。

immersion_word 从未发布过（建表的 d2f80fc177a2 同样只存在于当前未发布分支），
真实数据库里这张表有 0 行，没有需要保留的数据。因此这里直接 drop 再按新结构
重建，不做数据搬运；downgrade 对称地恢复旧的 (user_id, word_id) 结构。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7a1f4c9b2e63'
down_revision: Union[str, None] = 'd2f80fc177a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('immersion_word')
    op.create_table(
        'immersion_word',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('wordbook', sa.String(length=16), nullable=False),
        sa.Column('word_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), server_default='seen', nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['word_id'], ['word.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'wordbook', 'word_id', name='uq_immersion_word'),
    )
    op.create_index(
        op.f('ix_immersion_word_last_seen_at'), 'immersion_word', ['last_seen_at'], unique=False
    )
    op.create_index(
        op.f('ix_immersion_word_user_id'), 'immersion_word', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_immersion_word_word_id'), 'immersion_word', ['word_id'], unique=False
    )
    op.create_index(
        op.f('ix_immersion_word_wordbook'), 'immersion_word', ['wordbook'], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_immersion_word_wordbook'), table_name='immersion_word')
    op.drop_index(op.f('ix_immersion_word_word_id'), table_name='immersion_word')
    op.drop_index(op.f('ix_immersion_word_user_id'), table_name='immersion_word')
    op.drop_index(op.f('ix_immersion_word_last_seen_at'), table_name='immersion_word')
    op.drop_table('immersion_word')
    op.create_table(
        'immersion_word',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('word_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=16), server_default='seen', nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['word_id'], ['word.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'word_id', name='uq_immersion_word'),
    )
    op.create_index(
        op.f('ix_immersion_word_last_seen_at'), 'immersion_word', ['last_seen_at'], unique=False
    )
    op.create_index(
        op.f('ix_immersion_word_user_id'), 'immersion_word', ['user_id'], unique=False
    )
    op.create_index(
        op.f('ix_immersion_word_word_id'), 'immersion_word', ['word_id'], unique=False
    )
