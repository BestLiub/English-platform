from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Word
from ..schemas import WordbookOut

router = APIRouter(tags=["wordbook"])

BUILTIN_WORDBOOKS: list[WordbookOut] = [
    WordbookOut(key="cet4", name="四级", count=0, description="CET-4 核心词汇"),
    WordbookOut(key="cet6", name="六级", count=0, description="CET-6 核心词汇"),
    WordbookOut(key="ky", name="考研", count=0, description="考研英语大纲词汇"),
    WordbookOut(key="ielts", name="雅思", count=0, description="IELTS 高频词"),
    WordbookOut(key="toefl", name="托福", count=0, description="TOEFL 高频词"),
    WordbookOut(key="gre", name="GRE", count=0, description="GRE 词汇"),
]


@router.get("/wordbooks")
def list_wordbooks(db: Session = Depends(get_db)) -> dict:
    """内置词库不打表，直接按 ECDICT 的 tag 字段计数。"""
    data = []
    for item in BUILTIN_WORDBOOKS:
        count = db.scalar(
            select(func.count()).select_from(Word).where(Word.tag.like(f"%{item.key}%"))
        )
        data.append({**item.model_dump(), "count": int(count or 0)})
    return {"code": 0, "message": "ok", "data": data}
