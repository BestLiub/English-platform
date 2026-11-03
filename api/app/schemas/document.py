from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class DocumentSummary(BaseModel):
    id: int
    title: str
    source_type: str
    source_ref: str | None = None
    word_count: int = 0
    paragraph_count: int = 0
    created_at: datetime


class ParagraphOut(BaseModel):
    idx: int
    text: str


class DocumentDetail(DocumentSummary):
    paragraphs: list[ParagraphOut]
    last_paragraph_idx: int = 0


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class UrlImportRequest(BaseModel):
    url: HttpUrl


class ProgressRequest(BaseModel):
    last_paragraph_idx: int = Field(ge=0)


class AnnotationSpan(BaseModel):
    start: int
    end: int
    word: str
    translation: str | None = None
    word_id: int | None = None


class DictEntry(BaseModel):
    word_id: int | None = None
    word: str
    phonetic: str | None = None
    translation: str | None = None
    definition: str | None = None
    frq: int | None = None
    tag: str | None = None
    lemma: str | None = None
    in_user_words: bool = False
