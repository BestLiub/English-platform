"""数据模型。

字段设计对应计划书第五节。v0.2 的做题表还没有建，
但所有用户态的表都留了 user_id 字段，将来接多用户不用改结构。
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


def utcnow() -> datetime:
    """统一存不带时区的 UTC，SQLite 比较起来最省事。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Word(Base):
    """词条主表，数据来自 ECDICT。"""

    __tablename__ = "word"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    phonetic: Mapped[str | None] = mapped_column(String(128))
    translation: Mapped[str | None] = mapped_column(Text)
    definition: Mapped[str | None] = mapped_column(Text)
    pos: Mapped[str | None] = mapped_column(String(64))
    collins: Mapped[int | None] = mapped_column(Integer)
    oxford: Mapped[int | None] = mapped_column(Integer)
    bnc: Mapped[int | None] = mapped_column(Integer)
    frq: Mapped[int | None] = mapped_column(Integer)
    # cet4 / cet6 / ky / ielts / toefl / gre，空格分隔，选词库就是过滤这一列
    tag: Mapped[str | None] = mapped_column(String(128), index=True)
    # ECDICT 的词形变化串，用来反查原形
    exchange: Mapped[str | None] = mapped_column(Text)
    audio: Mapped[str | None] = mapped_column(String(128))

    # 划词查义按 lower(word) 匹配；77 万行全表扫描要 140ms，表达式索引后接近 0
    __table_args__ = (
        Index("ix_word_lower", func.lower(text("word"))),
        Index("ix_word_frq", "frq"),
    )


class WordForm(Base):
    """变形 -> 原形 的反查表，由 Word.exchange 生成。

    有了它，划词遇到 running / ran / runs 都能直接命中 run，
    不需要引入 spaCy 这种重量级依赖。
    """

    __tablename__ = "word_form"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form: Mapped[str] = mapped_column(String(128), index=True)
    lemma_id: Mapped[int] = mapped_column(ForeignKey("word.id", ondelete="CASCADE"), index=True)

    __table_args__ = (UniqueConstraint("form", "lemma_id", name="uq_word_form"),)


class Wordbook(Base):
    __tablename__ = "wordbook"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    source_tag: Mapped[str | None] = mapped_column(String(64))
    is_builtin: Mapped[bool] = mapped_column(Integer, default=1)


class WordbookWord(Base):
    """自定义词库的成员表。内置词库直接按 tag 过滤，不写这张表。"""

    __tablename__ = "wordbook_word"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    wordbook_id: Mapped[int] = mapped_column(ForeignKey("wordbook.id", ondelete="CASCADE"), index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("word.id", ondelete="CASCADE"), index=True)

    __table_args__ = (UniqueConstraint("wordbook_id", "word_id", name="uq_wordbook_word"),)


class UserWord(Base):
    """用户对某个词的掌握状态，FSRS 的卡片数据就存在这里。"""

    __tablename__ = "user_word"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("word.id", ondelete="CASCADE"), index=True)

    # FSRS 参数
    stability: Mapped[float] = mapped_column(Float, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, default=0.0)
    state: Mapped[int] = mapped_column(Integer, default=0)      # 0 新 1 学习中 2 复习 3 重学
    step: Mapped[int] = mapped_column(Integer, default=0)
    interval_days: Mapped[float] = mapped_column(Float, default=0.0)

    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    due: Mapped[datetime | None] = mapped_column(default=utcnow, index=True)
    last_review: Mapped[datetime | None] = mapped_column(default=None)
    first_seen: Mapped[datetime] = mapped_column(default=utcnow)

    # learning = 正常学习中；known = 一眼就会，跳过，以后不再出现在任何队列
    status: Mapped[str] = mapped_column(String(16), default="learning", server_default="learning")

    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_user_word"),)


class ReviewLog(Base):
    """每次评分的流水，统计页的数据源。"""

    __tablename__ = "review_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    user_word_id: Mapped[int] = mapped_column(ForeignKey("user_word.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)          # 1 Again 2 Hard 3 Good 4 Easy
    reviewed_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0)
    scheduled_days: Mapped[float] = mapped_column(Float, default=0.0)


class Document(Base):
    __tablename__ = "document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(32))   # pdf / epub / docx / txt / md / url
    source_ref: Mapped[str | None] = mapped_column(Text)   # 原始文件名或网址
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    meta_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    paragraphs: Mapped[list["Paragraph"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="Paragraph.idx"
    )


class Paragraph(Base):
    """段落就是翻译与阅读的最小单位。

    前端按 idx 回填译文，所以 idx 必须稳定，不要在中途重排。
    """

    __tablename__ = "paragraph"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"), index=True)
    idx: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    translation: Mapped[str | None] = mapped_column(Text)
    translation_model: Mapped[str | None] = mapped_column(String(64))
    translated_at: Mapped[datetime | None] = mapped_column(default=None)

    document: Mapped[Document] = relationship(back_populates="paragraphs")

    __table_args__ = (Index("ix_paragraph_doc_idx", "document_id", "idx", unique=True),)


class ReadingSession(Base):
    __tablename__ = "reading_session"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("document.id", ondelete="CASCADE"), index=True)
    mode: Mapped[str] = mapped_column(String(16), default="original")  # original / bilingual
    started_at: Mapped[datetime] = mapped_column(default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(default=None)
    last_paragraph_idx: Mapped[int] = mapped_column(Integer, default=0)


class ImmersionWord(Base):
    """沉浸模式的词状态，与 user_word 完全隔离。"""

    __tablename__ = "immersion_word"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    # 掌握状态按词库隔离：同一个词可以同时在 cet4 和 cet6，互不影响
    wordbook: Mapped[str] = mapped_column(String(16), index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("word.id", ondelete="CASCADE"), index=True)
    # seen = 出现过、未掌握；mastered = 用户点了跳过
    status: Mapped[str] = mapped_column(String(16), default="seen", server_default="seen")
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    __table_args__ = (
        UniqueConstraint("user_id", "wordbook", "word_id", name="uq_immersion_word"),
    )
