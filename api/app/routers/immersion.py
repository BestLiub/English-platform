from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Word
from ..schemas.immersion import NextRequest, ResetRequest, SkipRequest
from ..services import immersion

router = APIRouter(prefix="/immersion", tags=["immersion"])

USER_ID = 1


def _item(word: Word) -> dict:
    return {
        "word_id": word.id,
        "word": word.word,
        "phonetic": word.phonetic,
        "translation": word.translation,
    }


@router.post("/next")
def next_word(payload: NextRequest, db: Session = Depends(get_db)) -> dict:
    word = immersion.draw(db, payload.wordbook, USER_ID)
    state = immersion.progress(db, payload.wordbook, USER_ID)
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "word": _item(word) if word else None,
            "progress": state,
            "finished": word is None,
        },
    }


@router.post("/skip")
def skip(payload: SkipRequest, db: Session = Depends(get_db)) -> dict:
    if db.get(Word, payload.word_id) is None:
        raise HTTPException(status_code=404, detail="词条不存在")
    immersion.mark_mastered(db, payload.word_id, USER_ID)
    return {"code": 0, "message": "ok", "data": immersion.progress(db, payload.wordbook, USER_ID)}


@router.post("/reset")
def reset(payload: ResetRequest, db: Session = Depends(get_db)) -> dict:
    immersion.reset(db, payload.wordbook, USER_ID)
    return {"code": 0, "message": "ok", "data": immersion.progress(db, payload.wordbook, USER_ID)}


@router.get("/stats")
def stats(wordbook: str = Query("cet4"), db: Session = Depends(get_db)) -> dict:
    return {"code": 0, "message": "ok", "data": immersion.progress(db, wordbook, USER_ID)}
