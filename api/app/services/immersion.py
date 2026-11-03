"""沉浸模式：随机抽词，与 FSRS 完全隔离。"""
from __future__ import annotations

from sqlalchemy import delete, func, select
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
        # 只算当前词库里还没掌握的词，别的词库和已掌握的行不占窗口名额
        recent = (
            select(ImmersionWord.word_id)
            .join(Word, Word.id == ImmersionWord.word_id)
            .where(
                ImmersionWord.user_id == user_id,
                ImmersionWord.status != "mastered",
                _book_filter(wordbook),
            )
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


def mark_mastered(db: Session, word_id: int, user_id: int = 1) -> None:
    """用户点了跳过：已出现过的行改成 mastered，没出现过的直接建一行。"""
    row = db.scalar(
        select(ImmersionWord).where(
            ImmersionWord.user_id == user_id, ImmersionWord.word_id == word_id
        )
    )
    if row is None:
        db.add(ImmersionWord(user_id=user_id, word_id=word_id, status="mastered"))
    else:
        row.status = "mastered"
    db.commit()


def progress(db: Session, wordbook: str, user_id: int = 1) -> dict:
    """当前词库的总数、已掌握数、剩余数。"""
    total = int(
        db.scalar(select(func.count()).select_from(Word).where(_book_filter(wordbook))) or 0
    )
    mastered = int(
        db.scalar(
            select(func.count())
            .select_from(ImmersionWord)
            .join(Word, Word.id == ImmersionWord.word_id)
            .where(
                ImmersionWord.user_id == user_id,
                ImmersionWord.status == "mastered",
                _book_filter(wordbook),
            )
        )
        or 0
    )
    return {"total": total, "mastered": mastered, "remaining": total - mastered}


def reset(db: Session, wordbook: str, user_id: int = 1) -> int:
    """清空当前词库的沉浸记录（mastered 和 seen 都删），返回删除的行数。"""
    book_ids = select(Word.id).where(_book_filter(wordbook))
    result = db.execute(
        delete(ImmersionWord).where(
            ImmersionWord.user_id == user_id, ImmersionWord.word_id.in_(book_ids)
        )
    )
    db.commit()
    return int(result.rowcount or 0)
