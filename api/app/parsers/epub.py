"""EPUB 解析：遍历章节，把正文元素按顺序取成段落。"""
from __future__ import annotations

from pathlib import Path

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub

from . import ParsedDocument, ParseError

_BLOCK_TAGS = ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote")
_SKIP_TAGS = ("script", "style", "nav")


def parse(path: Path) -> ParsedDocument:
    try:
        book = epub.read_epub(str(path), options={"ignore_ncx": True})
    except Exception as exc:  # noqa: BLE001
        raise ParseError("打不开这个 EPUB：文件可能已损坏，或者不是标准的 EPUB") from exc

    paragraphs: list[str] = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        for tag in soup(_SKIP_TAGS):
            tag.decompose()

        for element in soup.find_all(_BLOCK_TAGS):
            # 外层已经收过一遍的内容不再重复收
            if element.find(_BLOCK_TAGS) is not None:
                continue
            text = element.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)

    if not paragraphs:
        raise ParseError("这个 EPUB 里没有抽到正文")

    titles = book.get_metadata("DC", "title")
    title = titles[0][0].strip() if titles and titles[0][0] else path.stem

    return ParsedDocument(title=title, source_type="epub", paragraphs=paragraphs)
