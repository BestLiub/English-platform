from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from ..config import DB_PATH
from ..db import engine
from ..services import srs

router = APIRouter(tags=["system"])


def _db_probe() -> dict:
    """真去读一次库，把路径、日志模式、词条数带回来。

    只判断文件存在是不够的——之前的"镜像损坏"里 health 一直返回 200，
    真正出问题的查询在别处，排错时看不到任何信息。
    """
    info: dict = {"path": str(DB_PATH), "exists": DB_PATH.exists()}
    try:
        with engine.connect() as conn:
            info["journal_mode"] = conn.execute(text("PRAGMA journal_mode")).scalar()
            info["words"] = conn.execute(text("SELECT COUNT(*) FROM word")).scalar()
            info["error"] = None
    except Exception as exc:  # noqa: BLE001  健康检查绝不能自己抛错
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info


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
            "db_info": _db_probe(),
        },
    }
