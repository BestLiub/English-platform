"""网页正文抽取：trafilatura 负责去掉导航、广告和评论区。"""
from __future__ import annotations

import trafilatura

from . import ParsedDocument, ParseError


def parse(url: str) -> ParsedDocument:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ParseError("抓不到这个网址的内容，检查一下链接和网络连接")

    text = trafilatura.extract(
        downloaded,
        url=url,
        include_comments=False,
        include_tables=True,
        favor_recall=True,
    )
    if not text:
        raise ParseError("这个页面没抽到正文，可能是纯图片、需要登录，或者是动态渲染的页面")

    paragraphs = [line.strip() for line in text.split("\n") if line.strip()]

    title = ""
    metadata = trafilatura.extract_metadata(downloaded)
    if metadata is not None and metadata.title:
        title = metadata.title.strip()

    return ParsedDocument(
        title=title or url,
        source_type="url",
        paragraphs=paragraphs,
        meta={"url": url},
    )
