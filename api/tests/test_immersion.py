from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import ImmersionWord
from app.services import immersion


def test_immersion_word_table_has_expected_columns():
    columns = set(ImmersionWord.__table__.columns.keys())
    assert columns == {"id", "user_id", "word_id", "status", "last_seen_at"}


def test_repeat_window_scales_with_pool():
    assert immersion.repeat_window(5700) == 50
    assert immersion.repeat_window(30) == 10
    assert immersion.repeat_window(3) == 1
    assert immersion.repeat_window(1) == 0


def test_draw_records_word_as_seen(db, seed_words):
    """抽中的词要写进 immersion_word：状态 seen，last_seen_at 有值。"""
    word = immersion.draw(db, "cet4")
    assert word is not None
    row = db.scalar(
        select(ImmersionWord).where(
            ImmersionWord.user_id == 1,
            ImmersionWord.word_id == word.id,
        )
    )
    assert row is not None
    assert row.status == "seen"
    assert row.last_seen_at is not None


def test_draw_skips_the_most_recent_words(db, seed_words):
    """cet4 有 6 个候选，窗口是 2：最近抽过的两个词这轮不进候选。"""
    db.add_all([
        ImmersionWord(user_id=1, word_id=seed_words["apple"], status="seen",
                      last_seen_at=datetime(2030, 1, 1)),
        ImmersionWord(user_id=1, word_id=seed_words["banana"], status="seen",
                      last_seen_at=datetime(2030, 1, 1) + timedelta(seconds=1)),
    ])
    db.commit()
    word = immersion.draw(db, "cet4")
    assert word is not None
    assert word.word not in {"apple", "banana"}


def test_repeat_window_stays_within_the_book_and_excludes_mastered(db, seed_words):
    """窗口只数当前词库、未掌握的词：别的词库和 mastered 的行不占名额。"""
    db.add_all([
        ImmersionWord(user_id=1, word_id=seed_words["grape"], status="seen",
                      last_seen_at=datetime(2100, 1, 1, 0, 0, 5)),
        ImmersionWord(user_id=1, word_id=seed_words["apple"], status="mastered",
                      last_seen_at=datetime(2100, 1, 1, 0, 0, 4)),
        ImmersionWord(user_id=1, word_id=seed_words["banana"], status="mastered",
                      last_seen_at=datetime(2100, 1, 1, 0, 0, 3)),
        ImmersionWord(user_id=1, word_id=seed_words["cherry"], status="seen",
                      last_seen_at=datetime(2029, 1, 1)),
    ])
    db.commit()
    # cet4 剩 4 个候选（cherry/date/elder/fig），窗口 = 1，只挡得住 cherry
    word = immersion.draw(db, "cet4")
    assert word is not None
    assert word.word in {"date", "elder", "fig"}


def test_draw_returns_word_from_the_book(db, seed_words):
    word = immersion.draw(db, "cet6")
    assert word is not None
    assert word.tag == "cet6"


def test_draw_never_returns_mastered_word(db, seed_words):
    db.add_all([
        immersion.ImmersionWord(user_id=1, word_id=seed_words["grape"], status="mastered"),
        immersion.ImmersionWord(user_id=1, word_id=seed_words["honey"], status="mastered"),
    ])
    db.commit()
    seen = set()
    for _ in range(20):
        word = immersion.draw(db, "cet6")
        assert word is not None
        seen.add(word.word)
    assert seen == {"iris"}


def test_draw_returns_none_when_everything_is_mastered(db, seed_words):
    db.add_all([
        immersion.ImmersionWord(user_id=1, word_id=wid, status="mastered")
        for wid in seed_words.values()
    ])
    db.commit()
    assert immersion.draw(db, "cet4") is None


def test_draw_gives_up_the_window_rather_than_getting_stuck(db, seed_words, monkeypatch):
    """窗口把候选全挡住时（池子只剩 2 个词，窗口也等于 2），必须退回去不过滤。"""
    db.add_all([
        immersion.ImmersionWord(user_id=1, word_id=wid, status="mastered")
        for name, wid in seed_words.items() if name not in {"grape", "honey"}
    ])
    db.add_all([
        immersion.ImmersionWord(user_id=1, word_id=seed_words[name], status="seen",
                                last_seen_at=datetime(2100, 1, 1) + timedelta(seconds=index))
        for index, name in enumerate(["grape", "honey"])
    ])
    db.commit()
    monkeypatch.setattr(immersion, "repeat_window", lambda count: count)
    drawn = {immersion.draw(db, "cet6").word for _ in range(20)}
    assert drawn == {"grape", "honey"}
