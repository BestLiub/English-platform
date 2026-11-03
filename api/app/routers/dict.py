from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import lexicon

router = APIRouter(prefix="/dict", tags=["dict"])

USER_ID = 1


@router.get("/{word}")
def define(word: str, db: Session = Depends(get_db)) -> dict:
    """划词查义。查不到返回 data=null，让前端自己决定怎么提示。"""
    entry = lexicon.lookup(db, word, user_id=USER_ID)
    return {"code": 0, "message": "ok", "data": entry}
