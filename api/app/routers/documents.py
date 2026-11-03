from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import UPLOAD_DIR
from ..db import get_db
from ..models import Document, Paragraph, ReadingSession
from ..parsers import SUPPORTED_EXTENSIONS, ParseError, parse_file, parse_url
from ..schemas.document import (
    DocumentDetail,
    DocumentSummary,
    ProgressRequest,
    RenameRequest,
    UrlImportRequest,
)
from ..services.annotation import STRATEGIES, annotate

router = APIRouter(prefix="/documents", tags=["documents"])

logger = logging.getLogger(__name__)

USER_ID = 1
MAX_UPLOAD_BYTES = 30 * 1024 * 1024


def _remove_quietly(path: Path) -> None:
    """删临时文件。删不掉（文件还被占用）不该盖住真正的错误。"""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("清理文件失败：%s", path)


def _summary(doc: Document, paragraph_count: int) -> dict:
    return DocumentSummary(
        id=doc.id,
        title=doc.title,
        source_type=doc.source_type,
        source_ref=doc.source_ref,
        word_count=doc.word_count,
        paragraph_count=paragraph_count,
        created_at=doc.created_at,
    ).model_dump()


def _get_or_404(db: Session, document_id: int) -> Document:
    doc = db.get(Document, document_id)
    if doc is None or doc.user_id != USER_ID:
        raise HTTPException(status_code=404, detail="文章不存在")
    return doc


def _paragraph_texts(db: Session, document_id: int) -> list[str]:
    return list(
        db.scalars(
            select(Paragraph.text).where(Paragraph.document_id == document_id).order_by(Paragraph.idx)
        ).all()
    )


def _store(db: Session, parsed, *, source_ref: str | None, meta: dict | None = None) -> Document:
    doc = Document(
        user_id=USER_ID,
        title=parsed.title[:200] or "未命名",
        source_type=parsed.source_type,
        source_ref=source_ref,
        word_count=parsed.word_count,
        meta_json=json.dumps({**parsed.meta, **(meta or {})}, ensure_ascii=False),
    )
    db.add(doc)
    db.flush()
    db.add_all(
        Paragraph(document_id=doc.id, idx=index, text=text)
        for index, text in enumerate(parsed.paragraphs)
    )
    db.commit()
    db.refresh(doc)
    return doc


@router.get("")
def list_documents(db: Session = Depends(get_db)) -> dict:
    counts = dict(
        db.execute(select(Paragraph.document_id, func.count()).group_by(Paragraph.document_id)).all()
    )
    docs = db.scalars(
        select(Document).where(Document.user_id == USER_ID).order_by(Document.created_at.desc())
    ).all()
    return {
        "code": 0,
        "message": "ok",
        "data": [_summary(doc, counts.get(doc.id, 0)) for doc in docs],
    }


@router.post("/upload")
async def upload(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail=f"不支持 {suffix or '这种'} 格式，支持 txt / md / pdf / docx / epub"
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件是空的")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="文件超过 30 MB，先拆小一点再传")

    stored = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    stored.write_bytes(content)
    try:
        parsed = parse_file(stored)
    except ParseError as exc:
        _remove_quietly(stored)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # 解析器拿到的文件名是随机串，这里换回用户原本的文件名
    if not parsed.title or parsed.title == stored.stem:
        parsed.title = Path(file.filename or "").stem or "未命名"

    doc = _store(db, parsed, source_ref=file.filename, meta={"stored_name": stored.name})
    return {"code": 0, "message": "ok", "data": _summary(doc, len(parsed.paragraphs))}


@router.post("/from-url")
def import_from_url(payload: UrlImportRequest, db: Session = Depends(get_db)) -> dict:
    try:
        parsed = parse_url(str(payload.url))
    except ParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    doc = _store(db, parsed, source_ref=str(payload.url))
    return {"code": 0, "message": "ok", "data": _summary(doc, len(parsed.paragraphs))}


@router.get("/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)) -> dict:
    doc = _get_or_404(db, document_id)
    paragraphs = db.scalars(
        select(Paragraph).where(Paragraph.document_id == doc.id).order_by(Paragraph.idx)
    ).all()

    session = db.scalar(
        select(ReadingSession)
        .where(ReadingSession.user_id == USER_ID, ReadingSession.document_id == doc.id)
        .order_by(ReadingSession.id.desc())
    )

    data = DocumentDetail(
        **_summary(doc, len(paragraphs)),
        paragraphs=[{"idx": p.idx, "text": p.text} for p in paragraphs],
        last_paragraph_idx=session.last_paragraph_idx if session else 0,
    ).model_dump()
    return {"code": 0, "message": "ok", "data": data}


@router.patch("/{document_id}")
def rename_document(document_id: int, payload: RenameRequest, db: Session = Depends(get_db)) -> dict:
    doc = _get_or_404(db, document_id)
    doc.title = payload.title.strip()[:200] or doc.title
    db.commit()
    count = db.scalar(
        select(func.count()).select_from(Paragraph).where(Paragraph.document_id == doc.id)
    )
    return {"code": 0, "message": "ok", "data": _summary(doc, int(count or 0))}


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)) -> dict:
    doc = _get_or_404(db, document_id)

    stored_name = None
    if doc.meta_json:
        try:
            stored_name = json.loads(doc.meta_json).get("stored_name")
        except json.JSONDecodeError:
            stored_name = None

    db.delete(doc)
    db.commit()

    if stored_name:
        _remove_quietly(UPLOAD_DIR / stored_name)

    return {"code": 0, "message": "ok", "data": {"id": document_id}}


@router.put("/{document_id}/progress")
def save_progress(document_id: int, payload: ProgressRequest, db: Session = Depends(get_db)) -> dict:
    doc = _get_or_404(db, document_id)

    session = db.scalar(
        select(ReadingSession)
        .where(ReadingSession.user_id == USER_ID, ReadingSession.document_id == doc.id)
        .order_by(ReadingSession.id.desc())
    )
    if session is None:
        session = ReadingSession(user_id=USER_ID, document_id=doc.id)
        db.add(session)

    session.last_paragraph_idx = payload.last_paragraph_idx
    db.commit()
    return {"code": 0, "message": "ok", "data": {"last_paragraph_idx": session.last_paragraph_idx}}


@router.get("/{document_id}/annotations")
def get_annotations(
    document_id: int,
    strategy: str = Query("beyond", description="beyond / unmastered / all"),
    wordbook: str = Query("cet4", description="用于判断超纲的词库 key"),
    db: Session = Depends(get_db),
) -> dict:
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=400, detail=f"未知的注释策略：{strategy}")

    _get_or_404(db, document_id)
    spans = annotate(
        db, _paragraph_texts(db, document_id), strategy=strategy, wordbook=wordbook, user_id=USER_ID
    )
    return {"code": 0, "message": "ok", "data": {"strategy": strategy, "paragraphs": spans}}
