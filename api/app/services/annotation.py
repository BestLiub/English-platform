"""生词注释：分词 → 还原原形 → 按策略挑出该提示的词。

全程本地计算，不落库：一次几百个词的查表很便宜，存下来反而要处理失效。
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import UserWord
from . import lexicon

STRATEGIES = ("beyond", "unmastered", "all")


_POS_PREFIX = re.compile(r"^[a-z]{1,5}\.\s*", re.IGNORECASE)
_SENSE_SEP = re.compile(r"[,，;；、]")


def _short_gloss(translation: str | None) -> str | None:
    """行间提示要短到比英文单词还窄，否则 ruby 盒子会把整行撑开。

    "vt. 发现, 找到, 暴露" -> "发现"
    """
    if not translation:
        return None
    first = translation.split("\n")[0].strip()
    first = _POS_PREFIX.sub("", first)
    first = _SENSE_SEP.split(first)[0].strip()
    first = first.strip("　 .。:：")
    if not first:
        return None
    return first[:6]


def annotate(
    db: Session,
    paragraphs: list[str],
    *,
    strategy: str,
    wordbook: str,
    user_id: int = 1,
) -> dict[str, list[dict]]:
    parsed: list[list[tuple[int, int, str]]] = []
    tokens: set[str] = set()
    for text in paragraphs:
        spans = lexicon.tokenize(text)
        parsed.append(spans)
        tokens.update(token for _, _, token in spans)

    resolved = lexicon.resolve_many(db, tokens)

    user_words = {
        row.word_id: row
        for row in db.scalars(select(UserWord).where(UserWord.user_id == user_id)).all()
    }
    mastered = {
        word_id
        for word_id, row in user_words.items()
        if row.stability >= lexicon.MASTERED_STABILITY
    }

    result: dict[str, list[dict]] = {}
    for idx, spans in enumerate(parsed):
        picked: list[dict] = []
        for start, end, token in spans:
            word = resolved.get(token)
            if word is None or word.id in mastered:
                continue

            # 太常见的词不标，否则一篇文章半屏都是提示
            if word.frq is not None and word.frq <= lexicon.COMMON_FRQ:
                continue

            if strategy == "beyond":
                # 在当前词库里 = 不算超纲，不标
                if word.tag and wordbook in word.tag.split():
                    continue
            elif strategy == "unmastered":
                # 已经开始学的词不标，留给背单词模块
                if word.id in user_words:
                    continue

            gloss = _short_gloss(word.translation)
            if not gloss:
                continue
            picked.append(
                {
                    "start": start,
                    "end": end,
                    "word": token,
                    "translation": gloss,
                    "word_id": word.id,
                }
            )

        if picked:
            result[str(idx)] = picked

    return result
