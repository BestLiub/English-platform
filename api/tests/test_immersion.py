from app.models import ImmersionWord


def test_immersion_word_table_has_expected_columns():
    columns = set(ImmersionWord.__table__.columns.keys())
    assert columns == {"id", "user_id", "word_id", "status", "last_seen_at"}
