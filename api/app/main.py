"""FastAPI 入口。

一个进程同时提供 API 和前端静态文件——这是启动器能做得这么简单的原因。
开发期前端由 Vite 在 5173 提供（带热更新），构建后由这里托管。
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import LOG_DIR, WEB_DIST
from .db import init_db
from .routers import documents, health, study, wordbooks
from .routers import dict as dict_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "api.log", encoding="utf-8"),
        ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("数据库就绪，前端产物: %s", WEB_DIST if WEB_DIST.exists() else "未构建（开发模式）")
    yield


app = FastAPI(title="English", version="0.1.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """兜底：把 traceback 写进 api.log，并把原始错误回给前端。

    默认的 500 既没有日志也没有消息，本地调试时只能瞎猜。
    """
    logger.exception("未处理的异常：%s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": f"{type(exc).__name__}: {exc}"})

# 只有开发期需要这两个来源；构建后同源，不会触发跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(wordbooks.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(dict_router.router, prefix="/api")

# 注意：catch-all 必须最后注册，否则会把 /api 也吃掉
if WEB_DIST.exists():
    _assets = WEB_DIST / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        target = (WEB_DIST / full_path).resolve()
        if full_path and target.is_file() and WEB_DIST.resolve() in target.parents:
            return FileResponse(target)
        return FileResponse(WEB_DIST / "index.html")

else:

    @app.get("/", include_in_schema=False)
    async def dev_hint() -> dict:
        return {
            "message": "前端还没构建。开发时请访问 http://127.0.0.1:5173，"
            "或先执行 npm run build。",
            "api_docs": "/docs",
        }
