"""查词与词形还原。

ECDICT 里 running / ran / runs 各自的 exchange 字段标了原形，
导入时已经生成 word_form 表，所以这里不需要 spaCy 这类分词模型。
"""
from __future__ import annotations

import re
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import UserWord, Word, WordForm

# 字母开头的词，允许中间带连字符和撇号（well-known / don't）
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")

_CHUNK = 500

# FSRS 稳定性超过这个天数就认为已经记住了，不再标注
MASTERED_STABILITY = 21.0

# 词频排名小于这个数的词太常见（the / over / quick），标出来只是噪音
COMMON_FRQ = 3000


def normalize(token: str) -> str:
    return token.strip().strip("'-").lower()


def tokenize(text: str) -> list[tuple[int, int, str]]:
    """返回 (start, end, 归一化后的词)。位置用于前端在原文字符串里定位。"""
    spans: list[tuple[int, int, str]] = []
    for match in WORD_RE.finditer(text):
        word = normalize(match.group())
        if len(word) > 1:
            spans.append((match.start(), match.end(), word))
    return spans


def resolve_many(db: Session, tokens: Iterable[str]) -> dict[str, Word]:
    """批量把词或变形映射到词条，返回 {token: Word}。"""
    pending = list({t for t in tokens if t})
    found: dict[str, Word] = {}

    for start in range(0, len(pending), _CHUNK):
        chunk = pending[start : start + _CHUNK]
        for word in db.scalars(select(Word).where(func.lower(Word.word).in_(chunk))).all():
            found[word.word.lower()] = word

    missing = [t for t in pending if t not in found]
    for start in range(0, len(missing), _CHUNK):
        chunk = missing[start : start + _CHUNK]
        rows = db.execute(
            select(WordForm.form, Word)
            .join(Word, Word.id == WordForm.lemma_id)
            .where(func.lower(WordForm.form).in_(chunk))
        ).all()
        for form, word in rows:
            found.setdefault(form.lower(), word)

    return found


def lookup(db: Session, raw: str, user_id: int = 1) -> dict | None:
    """划词查义：返回词条信息，命中变形时把原形也带上。"""
    token = normalize(raw)
    if not token:
        return None

    word = db.scalar(select(Word).where(func.lower(Word.word) == token))
    lemma = None
    if word is None:
        word = db.scalar(
            select(Word)
            .join(WordForm, WordForm.lemma_id == Word.id)
            .where(func.lower(WordForm.form) == token)
        )
        if word is not None:
            lemma = word.word

    if word is None:
        return None

    in_user_words = (
        db.scalar(
            select(UserWord.id).where(UserWord.user_id == user_id, UserWord.word_id == word.id)
        )
        is not None
    )

    return {
        "word_id": word.id,
        "word": word.word,
        "phonetic": word.phonetic,
        "translation": word.translation,
        "definition": word.definition,
        "frq": word.frq,
        "tag": word.tag,
        "lemma": lemma,
        "in_user_words": in_user_words,
    }
