from datetime import datetime, timedelta

from sqlalchemy import select

from app.models import ImmersionWord, Word
from app.services import immersion


def test_immersion_word_table_has_expected_columns():
    columns = set(ImmersionWord.__table__.columns.keys())
    assert columns == {"id", "user_id", "wordbook", "word_id", "status", "last_seen_at"}


def test_repeat_window_scales_with_pool():
    assert immersion.repeat_window(5700) == 50
    assert immersion.repeat_window(30) == 10
    assert immersion.repeat_window(3) == 1
    assert immersion.repeat_window(1) == 0


def test_draw_records_word_as_seen(db, seed_words):
    """抽中的词要写进 immersion_word：状态 seen，last_seen_at 有值，归属当前词库。"""
    word = immersion.draw(db, "cet4")
    assert word is not None
    row = db.scalar(
        select(ImmersionWord).where(
            ImmersionWord.user_id == 1,
            ImmersionWord.wordbook == "cet4",
            ImmersionWord.word_id == word.id,
        )
    )
    assert row is not None
    assert row.wordbook == "cet4"
    assert row.status == "seen"
    assert row.last_seen_at is not None


def test_draw_skips_the_most_recent_words(db, seed_words):
    """cet4 有 6 个候选，窗口是 2：最近抽过的两个词这轮不进候选。"""
    db.add_all([
        ImmersionWord(user_id=1, wordbook="cet4", word_id=seed_words["apple"], status="seen",
                      last_seen_at=datetime(2030, 1, 1)),
        ImmersionWord(user_id=1, wordbook="cet4", word_id=seed_words["banana"], status="seen",
                      last_seen_at=datetime(2030, 1, 1) + timedelta(seconds=1)),
    ])
    db.commit()
    word = immersion.draw(db, "cet4")
    assert word is not None
    assert word.word not in {"apple", "banana"}


def test_repeat_window_stays_within_the_book_and_excludes_mastered(db, seed_words):
    """窗口只数当前词库、未掌握的词：别的词库和 mastered 的行不占名额。"""
    db.add_all([
        ImmersionWord(user_id=1, wordbook="cet6", word_id=seed_words["grape"], status="seen",
                      last_seen_at=datetime(2100, 1, 1, 0, 0, 5)),
        ImmersionWord(user_id=1, wordbook="cet4", word_id=seed_words["apple"], status="mastered",
                      last_seen_at=datetime(2100, 1, 1, 0, 0, 4)),
        ImmersionWord(user_id=1, wordbook="cet4", word_id=seed_words["banana"], status="mastered",
                      last_seen_at=datetime(2100, 1, 1, 0, 0, 3)),
        ImmersionWord(user_id=1, wordbook="cet4", word_id=seed_words["cherry"], status="seen",
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
        ImmersionWord(user_id=1, wordbook="cet6", word_id=seed_words["grape"], status="mastered"),
        ImmersionWord(user_id=1, wordbook="cet6", word_id=seed_words["honey"], status="mastered"),
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
        ImmersionWord(user_id=1, wordbook="cet4", word_id=seed_words[name], status="mastered")
        for name in ["apple", "banana", "cherry", "date", "elder", "fig"]
    ])
    db.commit()
    assert immersion.draw(db, "cet4") is None


def test_draw_gives_up_the_window_rather_than_getting_stuck(db, seed_words, monkeypatch):
    """窗口把候选全挡住时（池子只剩 2 个词，窗口也等于 2），必须退回去不过滤。"""
    db.add(ImmersionWord(user_id=1, wordbook="cet6", word_id=seed_words["iris"],
                         status="mastered"))
    db.add_all([
        ImmersionWord(user_id=1, wordbook="cet6", word_id=seed_words[name], status="seen",
                      last_seen_at=datetime(2100, 1, 1) + timedelta(seconds=index))
        for index, name in enumerate(["grape", "honey"])
    ])
    db.commit()
    monkeypatch.setattr(immersion, "repeat_window", lambda count: count)
    drawn = {immersion.draw(db, "cet6").word for _ in range(20)}
    assert drawn == {"grape", "honey"}


def test_skip_marks_mastered_and_updates_progress(db, seed_words):
    immersion.mark_mastered(db, seed_words["grape"], "cet6")
    state = immersion.progress(db, "cet6")
    assert state == {"total": 3, "mastered": 1, "remaining": 2}


def test_reset_only_clears_the_requested_book(db, seed_words):
    immersion.mark_mastered(db, seed_words["grape"], "cet6")
    immersion.mark_mastered(db, seed_words["apple"], "cet4")
    immersion.reset(db, "cet6")
    assert immersion.progress(db, "cet6")["mastered"] == 0
    assert immersion.progress(db, "cet4")["mastered"] == 1


def test_reset_clears_seen_rows_too(db, seed_words):
    immersion.draw(db, "cet6")                          # 产生 seen 行
    removed = immersion.reset(db, "cet6")
    assert immersion.candidate_count(db, "cet6") == 3
    assert removed == 1                                 # 删掉的正是那条 seen 行
    assert db.scalars(select(ImmersionWord)).all() == []


def test_mark_mastered_updates_an_existing_seen_row(db, seed_words):
    """先抽到、再点跳过：已有的 seen 行要原地改成 mastered，不能留下 seen 状态。"""
    word = immersion.draw(db, "cet6")
    assert word is not None
    immersion.mark_mastered(db, word.id, "cet6")
    rows = db.scalars(
        select(ImmersionWord).where(
            ImmersionWord.wordbook == "cet6", ImmersionWord.word_id == word.id
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].status == "mastered"
    assert immersion.progress(db, "cet6")["mastered"] == 1


def test_mastery_is_per_wordbook_for_words_in_multiple_books(db, seed_words):
    """cet4 cet6 共有的词：两个词库各记各的，重置一个不能清掉另一个。"""
    db.add(Word(id=100, word="shared", tag="cet4 cet6"))
    db.commit()

    # 六级跳过：只记在六级账上，不算四级掌握
    immersion.mark_mastered(db, 100, "cet6")
    assert immersion.progress(db, "cet6")["mastered"] == 1
    assert immersion.progress(db, "cet4")["mastered"] == 0

    # 四级也掌握它：同一个词在两张词库的账上都有一行
    immersion.mark_mastered(db, 100, "cet4")
    assert immersion.progress(db, "cet4")["mastered"] == 1
    rows = db.scalars(select(ImmersionWord).where(ImmersionWord.word_id == 100)).all()
    assert {row.wordbook for row in rows} == {"cet4", "cet6"}

    cet4_before = immersion.progress(db, "cet4")
    immersion.reset(db, "cet6")

    # 重置六级不能动四级那一行
    assert immersion.progress(db, "cet4") == cet4_before
    assert immersion.progress(db, "cet4")["mastered"] == 1
    assert immersion.progress(db, "cet6")["mastered"] == 0
