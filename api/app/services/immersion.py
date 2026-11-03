"""沉浸模式：随机抽词，与 FSRS 完全隔离。"""
from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..models import ImmersionWord, Word
from .srs import utcnow

MAX_REPEAT_WINDOW = 50


def _book_filter(wordbook: str):
    return Word.tag.like(f"%{wordbook}%")


def _mastered_ids(user_id: int, wordbook: str):
    """只在同一个词库里算掌握：cet6 跳过不会让 cet4 里同名词条消失。"""
    return select(ImmersionWord.word_id).where(
        ImmersionWord.user_id == user_id,
        ImmersionWord.wordbook == wordbook,
        ImmersionWord.status == "mastered",
    )


def candidate_count(db: Session, wordbook: str, user_id: int = 1) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Word)
            .where(_book_filter(wordbook), Word.id.not_in(_mastered_ids(user_id, wordbook)))
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

    base = select(Word).where(
        _book_filter(wordbook), Word.id.not_in(_mastered_ids(user_id, wordbook))
    )

    window = repeat_window(remaining)
    word = None
    if window:
        # 只数当前词库的记录；别的词库的记录不占窗口名额
        recent = (
            select(ImmersionWord.word_id)
            .where(
                ImmersionWord.user_id == user_id,
                ImmersionWord.wordbook == wordbook,
                ImmersionWord.status != "mastered",
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

    _touch(db, word.id, wordbook, user_id)
    return word


def _touch(db: Session, word_id: int, wordbook: str, user_id: int = 1) -> None:
    row = db.scalar(
        select(ImmersionWord).where(
            ImmersionWord.user_id == user_id,
            ImmersionWord.wordbook == wordbook,
            ImmersionWord.word_id == word_id,
        )
    )
    if row is None:
        db.add(
            ImmersionWord(
                user_id=user_id,
                wordbook=wordbook,
                word_id=word_id,
                status="seen",
                last_seen_at=utcnow(),
            )
        )
    else:
        row.last_seen_at = utcnow()
    db.commit()


def mark_mastered(db: Session, word_id: int, wordbook: str, user_id: int = 1) -> None:
    """用户点了跳过：当前词库里已出现过的行改成 mastered，没出现过的直接建一行。"""
    row = db.scalar(
        select(ImmersionWord).where(
            ImmersionWord.user_id == user_id,
            ImmersionWord.wordbook == wordbook,
            ImmersionWord.word_id == word_id,
        )
    )
    if row is None:
        db.add(
            ImmersionWord(
                user_id=user_id,
                wordbook=wordbook,
                word_id=word_id,
                status="mastered",
            )
        )
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
            .where(
                ImmersionWord.user_id == user_id,
                ImmersionWord.wordbook == wordbook,
                ImmersionWord.status == "mastered",
            )
        )
        or 0
    )
    return {"total": total, "mastered": mastered, "remaining": total - mastered}


def reset(db: Session, wordbook: str, user_id: int = 1) -> int:
    """清空当前词库的沉浸记录（mastered 和 seen 都删），返回删除的行数。"""
    result = db.execute(
        delete(ImmersionWord).where(
            ImmersionWord.user_id == user_id,
            ImmersionWord.wordbook == wordbook,
        )
    )
    db.commit()
    return int(result.rowcount or 0)
