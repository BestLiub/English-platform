"""文档解析器集合。

约定：每个解析器接收原始内容，输出 ParsedDocument{title, source_type, paragraphs, meta}。
上层阅读器、注释、划词只认这一种结构，新增格式不需要动前端。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class ParseError(Exception):
    """解析失败。message 直接展示给用户，所以要用中文写清楚怎么办。"""


@dataclass
class ParsedDocument:
    title: str
    source_type: str
    paragraphs: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return sum(len(p.split()) for p in self.paragraphs)


SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx", ".epub"}


def parse_file(path: Path, *, title: str | None = None) -> ParsedDocument:
    """按扩展名分发到具体解析器，统一校验并补上标题。"""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".markdown"}:
        from .plain import parse
    elif suffix == ".pdf":
        from .pdf import parse
    elif suffix == ".docx":
        from .docx_parser import parse
    elif suffix == ".epub":
        from .epub import parse
    else:
        raise ParseError(f"暂不支持 {suffix or '这种'} 格式，目前支持 txt / md / pdf / docx / epub")

    document = parse(path)
    if title:
        document.title = title
    if not document.paragraphs:
        raise ParseError("没有解析出正文，换个文件试试")
    return document


def parse_url(url: str) -> ParsedDocument:
    from .web import parse

    document = parse(url)
    if not document.paragraphs:
        raise ParseError("没有从页面里抽到正文，可能是纯图片或需要登录")
    return document
