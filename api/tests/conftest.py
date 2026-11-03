import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Word  # noqa: F401  确保模型注册到 Base.metadata


@pytest.fixture
def db(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def seed_words(db):
    """造 6 个 cet4 词和 3 个 cet6 词，返回 {word: id}。"""
    words = [("apple", "cet4"), ("banana", "cet4"), ("cherry", "cet4"),
             ("date", "cet4"), ("elder", "cet4"), ("fig", "cet4"),
             ("grape", "cet6"), ("honey", "cet6"), ("iris", "cet6")]
    ids = {}
    for index, (text, tag) in enumerate(words, start=1):
        db.add(Word(id=index, word=text, tag=tag, frq=1000 + index))
        ids[text] = index
    db.commit()
    return ids
