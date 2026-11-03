from __future__ import annotations

from fastapi import APIRouter

from ..config import DB_PATH
from ..services import srs

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    """启动器轮询这个接口判断服务是否就绪，别删。"""
    return {
        "code": 0,
        "message": "ok",
        "data": {
            "status": "ok",
            "db": DB_PATH.exists(),
            "scheduler": "fsrs" if srs.is_available() else "fallback",
        },
    }
