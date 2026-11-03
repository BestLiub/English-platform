from app.models import ImmersionWord


def test_immersion_word_table_has_expected_columns():
    columns = set(ImmersionWord.__table__.columns.keys())
    assert columns == {"id", "user_id", "word_id", "status", "last_seen_at"}


from app.services import immersion


def test_repeat_window_scales_with_pool():
    assert immersion.repeat_window(5700) == 50
    assert immersion.repeat_window(30) == 10
    assert immersion.repeat_window(3) == 1
    assert immersion.repeat_window(1) == 0


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


def test_draw_gives_up_the_window_rather_than_getting_stuck(db, seed_words):
    """池子里只剩 2 个词时，窗口必须失效，否则会抽不出词。"""
    db.add_all([
        immersion.ImmersionWord(user_id=1, word_id=wid, status="mastered")
        for name, wid in seed_words.items() if name not in {"grape", "honey"}
    ])
    db.commit()
    drawn = {immersion.draw(db, "cet6").word for _ in range(20)}
    assert drawn == {"grape", "honey"}
