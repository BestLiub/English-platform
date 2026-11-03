"""数据库连接与会话。"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    # SQLite 默认禁止跨线程共享连接，FastAPI 的线程池会踩到这条限制
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表 / 升级表结构，走 Alembic。

    每次启动都 upgrade 到 head：首次运行会把迁移脚本建出的表一次性建好，
    之后改了模型只要补一个 revision，用户下次打开应用就自动完成升级。
    """
    from alembic import command
    from alembic.config import Config

    from .config import PROJECT_ROOT

    api_dir = PROJECT_ROOT / "api"
    cfg = Config()  # 不用 ini 文件，避免 fileConfig 覆盖掉自身的 logging 配置
    cfg.set_main_option("script_location", str(api_dir / "alembic"))
    cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(cfg, "head")
