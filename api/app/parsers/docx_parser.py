"""docx 解析：按段落取文本，表格里的一行拼成一句。"""
from __future__ import annotations

from pathlib import Path

import docx

from . import ParsedDocument, ParseError


def parse(path: Path) -> ParsedDocument:
    try:
        document = docx.Document(str(path))
    except Exception as exc:  # noqa: BLE001
        raise ParseError("打不开这个 Word 文件：可能不是 .docx，或者文件已损坏") from exc

    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]

    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    if not paragraphs:
        raise ParseError("这个 Word 文件里没有正文")

    return ParsedDocument(title=path.stem, source_type="docx", paragraphs=paragraphs)
