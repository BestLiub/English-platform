from __future__ import annotations

from pydantic import BaseModel


class NextRequest(BaseModel):
    wordbook: str = "cet4"


class SkipRequest(BaseModel):
    word_id: int
    wordbook: str = "cet4"


class ResetRequest(BaseModel):
    wordbook: str = "cet4"
