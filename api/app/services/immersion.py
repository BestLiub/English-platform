"""沉浸模式：随机抽词，与 FSRS 完全隔离。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import ImmersionWord, Word
from .srs import utcnow

MAX_REPEAT_WINDOW = 50


def _book_filter(wordbook: str):
    return Word.tag.like(f"%{wordbook}%")


def _mastered_ids(user_id: int):
    return select(ImmersionWord.word_id).where(
        ImmersionWord.user_id == user_id,
        ImmersionWord.status == "mastered",
    )


def candidate_count(db: Session, wordbook: str, user_id: int = 1) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Word)
            .where(_book_filter(wordbook), Word.id.not_in(_mastered_ids(user_id)))
        )
        or 0
    )


def repeat_window(count: int) -> int:
    """最近这么多个词不进候选，池子小时按比例缩小，永不等于池子大小。"""
    return min(MAX_REPEAT_WINDOW, count // 3)


def draw(db: Session, wordbook: str, user_id: int = 1) -> Word | None:
    remaining = candidate_count(db, wordbook, user_id)
    if remaining == 0:
        return None

    base = select(Word).where(_book_filter(wordbook), Word.id.not_in(_mastered_ids(user_id)))

    window = repeat_window(remaining)
    word = None
    if window:
        recent = (
            select(ImmersionWord.word_id)
            .where(ImmersionWord.user_id == user_id)
            .order_by(ImmersionWord.last_seen_at.desc())
            .limit(window)
        )
        word = db.scalar(
            base.where(Word.id.not_in(recent)).order_by(func.random()).limit(1)
        )
    if word is None:                      # 窗口把候选全挡住了，退回去不过滤
        word = db.scalar(base.order_by(func.random()).limit(1))
    if word is None:
        return None

    _touch(db, word.id, user_id)
    return word


def _touch(db: Session, word_id: int, user_id: int = 1) -> None:
    row = db.scalar(
        select(ImmersionWord).where(
            ImmersionWord.user_id == user_id, ImmersionWord.word_id == word_id
        )
    )
    if row is None:
        db.add(ImmersionWord(user_id=user_id, word_id=word_id, status="seen", last_seen_at=utcnow()))
    else:
        row.last_seen_at = utcnow()
    db.commit()
