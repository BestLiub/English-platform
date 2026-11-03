from datetime import timedelta

from app.models import UserWord, Word
from app.services.srs import utcnow


def _make_due(db, count: int):
    for index in range(1, count + 1):
        db.add(Word(id=index, word=f"w{index}", tag="cet4", frq=index))
        db.add(UserWord(user_id=1, word_id=index, due=utcnow() - timedelta(hours=1)))
    db.commit()


def test_plan_respects_review_limit(db):
    from app.routers.study import get_plan
    _make_due(db, 30)
    data = get_plan(wordbook="cet4", new_limit=0, review_limit=10, db=db)["data"]
    assert len(data["reviews"]) == 10


def test_review_limit_zero_returns_no_reviews(db):
    from app.routers.study import get_plan
    _make_due(db, 5)
    data = get_plan(wordbook="cet4", new_limit=0, review_limit=0, db=db)["data"]
    assert data["reviews"] == []
