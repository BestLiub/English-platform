"""PDF 解析：取文本层，丢掉页眉页脚，合并断行。

不渲染原版面——目标是把内容变成可选择的文本，不是复刻排版。
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pymupdf

from . import ParsedDocument, ParseError

# 页面上下这么高的区域算"边缘"，页眉页脚只会出现在这里
EDGE_RATIO = 0.12
# 边缘上的短文本要短于这个长度才可能是页眉页脚
EDGE_MAX_LEN = 80

_HYPHEN_BREAK = re.compile(r"-\n(?=[a-z])")
_PAGE_NUMBER = re.compile(r"^[-–—\s]*\d{1,4}[-–—\s]*$")


def _clean_block(text: str) -> str:
    text = text.replace("­", "")          # 软连字符
    text = _HYPHEN_BREAK.sub("", text)         # exam-\nple -> example
    text = re.sub(r"\s*\n\s*", " ", text)      # 段内断行合并
    return text.strip()


def _signature(text: str) -> str:
    """把数字抹平，让 "Page 1" 和 "Page 2" 算同一种页眉。"""
    return re.sub(r"\d+", "#", text.lower())


def parse(path: Path) -> ParsedDocument:
    # 用内存流打开：PyMuPDF 打开失败时不会释放文件句柄，
    # 而 Windows 不允许删除仍被占用的文件，会让上层清理临时文件直接报错。
    try:
        document = pymupdf.open(stream=path.read_bytes(), filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        raise ParseError(f"打不开这个 PDF：文件可能已损坏或不是真正的 PDF") from exc

    try:
        pages: list[tuple[float, list[tuple[float, float, str]]]] = []
        for page in document:
            height = page.rect.height
            blocks: list[tuple[float, float, str]] = []
            for _x0, y0, _x1, y1, text, _no, block_type in page.get_text("blocks"):
                if block_type != 0:
                    continue                    # 图片块
                cleaned = _clean_block(text)
                if cleaned:
                    blocks.append((y0, y1, cleaned))
            pages.append((height, blocks))

        meta_title = (document.metadata or {}).get("title") or ""
    finally:
        document.close()

    # 第一遍：统计上下边缘出现过多次的短文本，它们就是页眉页脚
    edge_counts: Counter[str] = Counter()
    for height, blocks in pages:
        for y0, y1, text in blocks:
            if len(text) > EDGE_MAX_LEN:
                continue
            middle = (y0 + y1) / 2
            if middle <= height * EDGE_RATIO or middle >= height * (1 - EDGE_RATIO):
                edge_counts[_signature(text)] += 1

    repeated = {key for key, count in edge_counts.items() if count >= 2}

    # 第二遍：收正文
    paragraphs: list[str] = []
    for height, blocks in pages:
        for y0, y1, text in blocks:
            if _PAGE_NUMBER.match(text):
                continue
            middle = (y0 + y1) / 2
            at_edge = middle <= height * EDGE_RATIO or middle >= height * (1 - EDGE_RATIO)
            if at_edge and _signature(text) in repeated:
                continue
            paragraphs.append(text)

    if not paragraphs:
        raise ParseError("这个 PDF 没有文本层，可能是扫描件。可以用「粘贴文本」先导入正文。")

    return ParsedDocument(
        title=meta_title.strip() or path.stem,
        source_type="pdf",
        paragraphs=paragraphs,
    )
