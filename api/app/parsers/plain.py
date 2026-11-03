"""txt / md 解析：按空行切段，md 顺手去掉标记符号。"""
from __future__ import annotations

import re
from pathlib import Path

from . import ParsedDocument, ParseError

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_FENCE = re.compile(r"^\s*```.*$", re.MULTILINE)
_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_EMPHASIS = re.compile(r"\*\*|__|\*|_|`")


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            title = line.lstrip("#").strip()
            if title:
                return title
    return None


def _split_paragraphs(text: str) -> list[str]:
    blocks = re.split(r"\n\s*\n", text)
    return [re.sub(r"\s*\n\s*", " ", block).strip() for block in blocks if block.strip()]


def parse(path: Path) -> ParsedDocument:
    raw = path.read_text(encoding="utf-8", errors="replace")
    is_markdown = path.suffix.lower() in {".md", ".markdown"}

    if is_markdown:
        title = _first_heading(raw) or path.stem
        raw = _FENCE.sub("", raw)
        raw = _HEADING.sub("", raw)
        raw = _LINK.sub(r"\1", raw)
        raw = _EMPHASIS.sub("", raw)
    else:
        title = path.stem

    paragraphs = _split_paragraphs(raw)
    if not paragraphs:
        raise ParseError("文件里没有可读的正文")

    return ParsedDocument(
        title=title,
        source_type="md" if is_markdown else "txt",
        paragraphs=paragraphs,
    )
