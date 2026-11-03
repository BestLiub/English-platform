#!/usr/bin/env python3
"""把 ECDICT 的 CSV 导入本地 SQLite。

用法：
    uv run python ../scripts/import_ecdict.py                 # 自动下载
    uv run python ../scripts/import_ecdict.py --csv path.csv  # 用本地文件
    uv run python ../scripts/import_ecdict.py --limit 50000   # 只导前 N 行做测试
    uv run python ../scripts/import_ecdict.py --tagged-only   # 只导带考试标签的词

ECDICT 仓库：https://github.com/skywind3000/ECDICT
"""
from __future__ import annotations

import argparse
import csv
import sqlite3
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from app.config import APP_HOME, DB_PATH  # noqa: E402
from app.db import init_db  # noqa: E402

CANDIDATE_URLS = [
    "https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv",
]

EXAM_TAGS = ("cet4", "cet6", "ky", "ielts", "toefl", "gre")

# exchange 字段的键：这些是"本词是原形，值是它的变形"
FORM_KEYS = set("p d i 3 r t s")
# 这些是"本词是变形，值是原形"
LEMMA_KEYS = {"0", "1"}


def download(dest: Path, retries: int = 3) -> Path:
    """下载词库，支持断点续传。

    ecdict.csv 有 60 多 MB，国内直连 GitHub 经常在最后一段断开，
    所以下载写进 .part 文件、每次从已有的字节数续传，而不是整份重来。
    """
    if dest.exists() and dest.stat().st_size > 1024:
        print(f"已存在词库文件，跳过下载：{dest}")
        return dest

    partial = dest.with_suffix(".part")
    for url in CANDIDATE_URLS:
        for attempt in range(1, retries + 1):
            done = partial.stat().st_size if partial.exists() else 0
            req = urllib.request.Request(url)
            if done:
                req.add_header("Range", f"bytes={done}-")
            try:
                print(
                    f"正在下载 {url}"
                    + (f"（从 {done // 1048576} MB 续传，第 {attempt} 次）" if done else "")
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    # 服务端不认 Range 时会返回 200 的完整内容，此时只能从头写
                    if done and resp.status != 206:
                        done = 0
                        partial.unlink(missing_ok=True)
                    total = int(resp.headers.get("Content-Length") or 0) + done
                    with partial.open("ab") as fh:
                        while chunk := resp.read(1 << 20):
                            fh.write(chunk)
                            done += len(chunk)
                            if total:
                                pct = done * 100 // total
                                print(f"\r  {pct:3d}%  {done // 1048576} MB", end="", flush=True)
                print()
                partial.replace(dest)
                return dest
            except Exception as exc:  # noqa: BLE001
                kept = partial.stat().st_size if partial.exists() else 0
                print(f"  失败：{exc}（已保留 {kept // 1048576} MB，下次续传）")

    raise SystemExit(
        "\n自动下载失败。请手动下载 ecdict.csv 后重试：\n"
        "  1. 打开 https://github.com/skywind3000/ECDICT\n"
        "  2. 下载 ecdict.csv\n"
        f"  3. 放到 {dest}\n"
        "  4. 重新执行本脚本"
    )


def clean_text(raw: str | None) -> str | None:
    """ECDICT 的释义/英释里用字面量 \\n 表示换行，导入时还原成真正的换行符，
    否则前端会原样显示出反斜杠和 n。"""
    value = (raw or "").replace("\\n", "\n").strip()
    return value or None


def parse_exchange(raw: str) -> tuple[list[str], list[str]]:
    """返回 (本词的变形列表, 本词所属的原形列表)。"""
    forms: list[str] = []
    lemmas: list[str] = []
    if not raw:
        return forms, lemmas
    for part in raw.split("/"):
        key, _, value = part.partition(":")
        key, value = key.strip(), value.strip()
        if not value:
            continue
        if key in FORM_KEYS:
            forms.append(value)
        elif key in LEMMA_KEYS:
            lemmas.append(value)
    return forms, lemmas


def main() -> None:
    parser = argparse.ArgumentParser(description="导入 ECDICT 到本地 SQLite")
    parser.add_argument("--csv", type=Path, help="本地 ecdict.csv 路径")
    parser.add_argument("--limit", type=int, default=0, help="只导入前 N 条，调试用")
    parser.add_argument("--tagged-only", action="store_true", help="只导入带考试标签的词")
    args = parser.parse_args()

    csv_path = args.csv or download(APP_HOME / "data" / "ecdict.csv")
    if not csv_path.exists():
        raise SystemExit(f"找不到 CSV：{csv_path}")

    print("初始化表结构…")
    init_db()

    conn = sqlite3.connect(DB_PATH)
    # 单人本地应用用不上 WAL 的并发能力，反而会留下 -wal/-shm 两个附属文件：
    # 多个进程交替打开时，短命连接退出会截断 WAL，让长连接读到损坏的共享内存索引。
    conn.execute("PRAGMA journal_mode=DELETE")
    conn.execute("PRAGMA synchronous=OFF")

    existing = {row[0] for row in conn.execute("SELECT word FROM word")}
    next_id = (conn.execute("SELECT COALESCE(MAX(id), 0) FROM word").fetchone()[0]) + 1
    print(f"已有词条 {len(existing)} 条")

    word_rows: list[tuple] = []
    form_rows: list[tuple] = []
    # 先把变形收集起来，等词都插完再一次反查原形 id
    pending_forms: list[tuple[str, str]] = []
    inserted = 0

    def flush() -> None:
        nonlocal inserted
        if word_rows:
            conn.executemany(
                "INSERT OR IGNORE INTO word "
                "(id, word, phonetic, translation, definition, pos, collins, oxford, bnc, frq, tag, exchange, audio) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                word_rows,
            )
            inserted += len(word_rows)
            word_rows.clear()
        if form_rows:
            conn.executemany(
                "INSERT OR IGNORE INTO word_form (form, lemma_id) VALUES (?,?)",
                form_rows,
            )
            form_rows.clear()
        conn.commit()

    def to_int(value: str) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            if args.limit and i >= args.limit:
                break

            word = (row.get("word") or "").strip()
            if not word or len(word) > 100 or word in existing:
                continue

            tag = (row.get("tag") or "").strip().lower()
            if args.tagged_only and not any(t in tag for t in EXAM_TAGS):
                continue

            wid = next_id
            next_id += 1
            existing.add(word)

            word_rows.append(
                (
                    wid,
                    word,
                    (row.get("phonetic") or "").strip() or None,
                    clean_text(row.get("translation")),
                    clean_text(row.get("definition")),
                    (row.get("pos") or "").strip() or None,
                    to_int(row.get("collins") or ""),
                    to_int(row.get("oxford") or ""),
                    to_int(row.get("bnc") or ""),
                    to_int(row.get("frq") or ""),
                    tag or None,
                    (row.get("exchange") or "").strip() or None,
                    (row.get("audio") or "").strip() or None,
                )
            )

            forms, lemmas = parse_exchange((row.get("exchange") or "").strip())
            for form in forms:
                if form != word:
                    form_rows.append((form, wid))
            for lemma in lemmas:
                pending_forms.append((word, lemma))

            if len(word_rows) >= 5000:
                flush()
                print(f"\r  已导入 {inserted:,} 条", end="", flush=True)

    flush()
    print(f"\n词条导入完成：{inserted:,} 条")

    # 第二遍：把 "变形 -> 原形" 的关系补上
    if pending_forms:
        print(f"补齐 {len(pending_forms):,} 条词形关系…")
        id_by_word = {}
        batch = 2000
        for start in range(0, len(pending_forms), batch):
            chunk = pending_forms[start : start + batch]
            names = [w for _, w in chunk]
            placeholders = ",".join("?" * len(names))
            for wid, name in conn.execute(
                f"SELECT id, word FROM word WHERE word IN ({placeholders})", names
            ):
                id_by_word[name] = wid
        conn.executemany(
            "INSERT OR IGNORE INTO word_form (form, lemma_id) VALUES (?,?)",
            [
                (form, id_by_word[lemma])
                for form, lemma in pending_forms
                if lemma in id_by_word
            ],
        )
        conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM word").fetchone()[0]
    tagged = conn.execute(
        "SELECT COUNT(*) FROM word WHERE tag IS NOT NULL AND tag != ''"
    ).fetchone()[0]
    forms_total = conn.execute("SELECT COUNT(*) FROM word_form").fetchone()[0]
    conn.execute("CREATE INDEX IF NOT EXISTS ix_word_frq ON word(frq)")
    conn.commit()
    conn.close()

    print(f"词条 {total:,} 条，其中带考试标签 {tagged:,} 条，词形 {forms_total:,} 条")
    print(f"数据库位置：{DB_PATH}")


if __name__ == "__main__":
    main()
