from __future__ import annotations

from datetime import timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ReviewLog, UserWord, Word
from ..schemas import PlanItem, ReviewRequest, VocabularyRequest
from ..services import srs

router = APIRouter(prefix="/study", tags=["study"])

# v0.1 单用户，等接多用户时从请求里取
USER_ID = 1


def _to_item(word: Word, is_new: bool) -> dict:
    return PlanItem(
        word_id=word.id,
        word=word.word,
        phonetic=word.phonetic,
        translation=word.translation,
        is_new=is_new,
    ).model_dump()


@router.get("/plan")
def get_plan(
    wordbook: str = Query("cet4", description="词库 key，对应 ECDICT 的 tag"),
    new_limit: int = Query(20, ge=0, le=200),
    review_limit: int = Query(100, ge=0, le=1000, description="今日最多出多少张复习卡"),
    db: Session = Depends(get_db),
) -> dict:
    """今日队列：到期的复习卡优先，新词按上限补足。"""
    now = srs.utcnow()

    due_rows = db.scalars(
        select(UserWord)
        .where(
            UserWord.user_id == USER_ID,
            UserWord.due <= now,
            UserWord.status != "known",
        )
        .order_by(UserWord.due)
        .limit(review_limit)
    ).all()

    reviews: list[dict] = []
    if due_rows:
        words = {
            w.id: w
            for w in db.scalars(select(Word).where(Word.id.in_([r.word_id for r in due_rows]))).all()
        }
        for row in due_rows:
            word = words.get(row.word_id)
            if word is not None:
                reviews.append(_to_item(word, is_new=False))

    new_words: list[dict] = []
    if new_limit > 0:
        seen = select(UserWord.word_id).where(UserWord.user_id == USER_ID)
        rows = db.scalars(
            select(Word)
            .where(Word.tag.like(f"%{wordbook}%"))
            .where(Word.id.not_in(seen))
            .order_by(func.coalesce(Word.frq, 999999))
            .limit(new_limit)
        ).all()
        new_words = [_to_item(w, is_new=True) for w in rows]

    return {"code": 0, "message": "ok", "data": {"reviews": reviews, "new_words": new_words}}


@router.post("/review")
def submit_review(payload: ReviewRequest, db: Session = Depends(get_db)) -> dict:
    """提交一次评分，更新 FSRS 状态并写流水。"""
    word = db.get(Word, payload.word_id)
    if word is None:
        raise HTTPException(status_code=404, detail="词条不存在")

    user_word = db.scalar(
        select(UserWord).where(UserWord.user_id == USER_ID, UserWord.word_id == word.id)
    )
    if user_word is None:
        user_word = UserWord(user_id=USER_ID, word_id=word.id, due=srs.utcnow())
        db.add(user_word)
        db.flush()

    state = srs.CardState(
        stability=user_word.stability,
        difficulty=user_word.difficulty,
        state=user_word.state,
        step=user_word.step,
        interval_days=user_word.interval_days,
        reps=user_word.reps,
        lapses=user_word.lapses,
        due=user_word.due,
        last_review=user_word.last_review,
    )
    result = srs.review(state, payload.rating)

    user_word.stability = result.state.stability
    user_word.difficulty = result.state.difficulty
    user_word.state = result.state.state
    user_word.step = result.state.step
    user_word.interval_days = result.state.interval_days
    user_word.reps = result.state.reps
    user_word.lapses = result.state.lapses
    user_word.due = result.state.due
    user_word.last_review = result.state.last_review

    db.add(
        ReviewLog(
            user_id=USER_ID,
            user_word_id=user_word.id,
            rating=payload.rating,
            elapsed_ms=payload.elapsed_ms,
            scheduled_days=result.interval_days,
        )
    )
    db.commit()

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "next_due": (result.state.due or srs.utcnow()).isoformat(),
            "interval_days": round(result.interval_days, 4),
            "scheduler": result.source,
        },
    }


@router.post("/skip")
def skip_word(payload: VocabularyRequest, db: Session = Depends(get_db)) -> dict:
    """一眼就会的词，标记为已掌握：不再当新词推送，也不会进复习队列。"""
    word = db.get(Word, payload.word_id)
    if word is None:
        raise HTTPException(status_code=404, detail="词条不存在")

    user_word = db.scalar(
        select(UserWord).where(UserWord.user_id == USER_ID, UserWord.word_id == word.id)
    )
    if user_word is None:
        user_word = UserWord(user_id=USER_ID, word_id=word.id, due=srs.utcnow())
        db.add(user_word)

    user_word.status = "known"
    db.commit()

    return {"code": 0, "message": "ok", "data": {"word": word.word, "status": "known"}}


@router.post("/vocabulary")
def add_vocabulary(payload: VocabularyRequest, db: Session = Depends(get_db)) -> dict:
    """把精读时划到的词加进学习队列——这是精读和背单词真正咬合的地方。"""
    word = db.get(Word, payload.word_id)
    if word is None:
        raise HTTPException(status_code=404, detail="词条不存在")

    existing = db.scalar(
        select(UserWord).where(UserWord.user_id == USER_ID, UserWord.word_id == word.id)
    )
    if existing is not None:
        return {"code": 0, "message": "ok", "data": {"added": False, "word": word.word}}

    db.add(UserWord(user_id=USER_ID, word_id=word.id, due=srs.utcnow()))
    db.commit()
    return {"code": 0, "message": "ok", "data": {"added": True, "word": word.word}}


@router.get("/stats")
def stats(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)) -> dict:
    """按天聚合复习量，给统计页画曲线用。

    reviewed_at 存的是 UTC，而"每天"应该按用户本地日期切分，
    否则北京时间凌晨背的词会被算到前一天。这个应用跑在用户自己机器上，
    所以直接用服务器本地时区换算即可。
    """
    since = srs.utcnow() - timedelta(days=days)
    rows = db.execute(
        select(ReviewLog.reviewed_at, ReviewLog.rating).where(
            ReviewLog.user_id == USER_ID, ReviewLog.reviewed_at >= since
        )
    ).all()

    buckets: dict[str, dict[str, int]] = {}
    for reviewed_at, rating in rows:
        local_day = reviewed_at.replace(tzinfo=timezone.utc).astimezone().date().isoformat()
        bucket = buckets.setdefault(local_day, {"total": 0, "good": 0})
        bucket["total"] += 1
        if rating >= 3:
            bucket["good"] += 1

    total_reviews = db.scalar(select(func.count()).select_from(ReviewLog).where(ReviewLog.user_id == USER_ID)) or 0
    good_reviews = (
        db.scalar(
            select(func.count())
            .select_from(ReviewLog)
            .where(ReviewLog.user_id == USER_ID, ReviewLog.rating >= 3)
        )
        or 0
    )
    learned = db.scalar(select(func.count()).select_from(UserWord).where(UserWord.user_id == USER_ID)) or 0

    return {
        "code": 0,
        "message": "ok",
        "data": {
            "daily": [
                {"date": day, "total": b["total"], "good": b["good"]}
                for day, b in sorted(buckets.items())
            ],
            "total_reviews": int(total_reviews),
            "good_reviews": int(good_reviews),
            "learned_words": int(learned),
        },
    }
