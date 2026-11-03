from __future__ import annotations

from pydantic import BaseModel, Field


class WordbookOut(BaseModel):
    key: str
    name: str
    count: int
    description: str | None = None


class PlanItem(BaseModel):
    word_id: int
    word: str
    phonetic: str | None = None
    translation: str | None = None
    is_new: bool = False


class StudyPlan(BaseModel):
    reviews: list[PlanItem]
    new_words: list[PlanItem]


class ReviewRequest(BaseModel):
    word_id: int
    rating: int = Field(ge=1, le=4, description="1 忘了 / 2 勉强 / 3 记得 / 4 太简单")
    elapsed_ms: int = Field(default=0, ge=0)


class ReviewResponse(BaseModel):
    next_due: str
    interval_days: float
    scheduler: str


class VocabularyRequest(BaseModel):
    word_id: int
