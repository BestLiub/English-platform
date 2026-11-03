"""全局配置：路径、数据库、模型参数。

所有可变状态都放在用户目录下（Windows 是 %APPDATA%\\english-app），
不放仓库里——否则 git pull 或者重新构建会顺手把学习记录删掉。
"""
from __future__ import annotations

import os
from pathlib import Path


def _app_home() -> Path:
    explicit = os.environ.get("ENGLISH_HOME")
    if explicit:
        return Path(explicit)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "english-app"
    return Path.home() / ".english-app"


APP_HOME = _app_home()
DATA_DIR = APP_HOME / "data"
UPLOAD_DIR = APP_HOME / "uploads"
LOG_DIR = APP_HOME / "logs"

for _d in (APP_HOME, DATA_DIR, UPLOAD_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "english.db"

# as_posix() 很关键：Windows 的反斜杠塞进 sqlite URL 会解析失败
DATABASE_URL = os.environ.get("ENGLISH_DATABASE_URL") or f"sqlite:///{DB_PATH.as_posix()}"

# api/app/config.py -> api/app -> api -> 仓库根
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WEB_DIST = PROJECT_ROOT / "web" / "dist"

# 词库路径：导入脚本把 ECDICT 的 CSV 放在这里
ECDICT_CSV = DATA_DIR / "ecdict.csv"
