from __future__ import annotations

from pydantic import BaseModel, Field


class NextRequest(BaseModel):
    wordbook: str = Field(default="cet4", min_length=1)


class SkipRequest(BaseModel):
    word_id: int
    wordbook: str = Field(default="cet4", min_length=1)


class ResetRequest(BaseModel):
    wordbook: str = Field(default="cet4", min_length=1)
