import asyncio
import hashlib
import logging
from pathlib import Path

from fastapi import UploadFile, File, HTTPException, APIRouter, Request

from parsers.docx_parser import extract_text_from_docx
from parsers.epub_new import extract_text_from_epub
from parsers.fb2 import extract_text_from_fb2
from parsers.simple_pdf import extract_text_from_pdf
from persistence.chroma import Chroma
from util import smart_chunking

logger = logging.getLogger(__name__)

router = APIRouter()

_FILES_DIR = Path(__file__).parent.parent.parent / "files"

MAX_FILE_SIZE = 60 * 1024 * 1024  # 60 MB

_MAGIC: list[tuple[bytes, str]] = [
    (b'%PDF', 'pdf'),
    (b'PK\x03\x04', 'zip'),
    (b'\xd0\xcf\x11\xe0', 'ole'),
    (b'<?xml', 'xml'),
    (b'<Fict', 'xml'),
]

_EXT_TO_MAGIC = {
    'pdf': {'pdf'},
    'docx': {'zip'},
    'doc': {'ole'},
    'epub': {'zip'},
    'fb2': {'xml'},
}


def _validate(filename: str, content: bytes) -> None:
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 60 MB)")

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in _EXT_TO_MAGIC:
        raise HTTPException(400, f"Unsupported file format: .{ext}. Supported: pdf, docx, epub, fb2")

    header = content[:8]
    detected = None
    for magic, tag in _MAGIC:
        if header.startswith(magic):
            detected = tag
            break

    if detected is None or detected not in _EXT_TO_MAGIC[ext]:
        raise HTTPException(400, f"File content does not match .{ext} format")


def _save(filename: str, content: bytes) -> None:
    safe_name = Path(filename).name
    dest = _FILES_DIR / safe_name
    try:
        dest.resolve().relative_to(_FILES_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "Invalid filename")
    _FILES_DIR.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)


def _chunk_id(filename: str, index: int) -> str:
    safe = hashlib.sha1(filename.encode()).hexdigest()[:16]
    return f"{safe}_chunk_{index}"


@router.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), request: Request = None):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 60 MB)")

    try:
        file_content = await file.read()
    except Exception:
        logger.exception("Failed to read uploaded file")
        raise HTTPException(status_code=500, detail="Failed to read uploaded file")

    try:
        _validate(file.filename, file_content)
    except HTTPException:
        raise

    try:
        ext = file.filename.rsplit('.', 1)[-1].lower()

        if ext == 'pdf':
            full_text = extract_text_from_pdf(file_content)
        elif ext == 'fb2':
            full_text = extract_text_from_fb2(file_content)
        elif ext == 'epub':
            epub_data = extract_text_from_epub(file_content)
            full_text = "\n\n".join(ch['content'] for ch in epub_data.get('chapters', []))
        else:  # docx
            full_text = extract_text_from_docx(file_content)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to parse document: %s", file.filename)
        raise HTTPException(status_code=422, detail="Failed to parse document")

    if not full_text or not full_text.strip():
        raise HTTPException(status_code=422, detail="Document contains no extractable text")

    chunks = smart_chunking(full_text)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document produced no text chunks")

    documents = [chunk['text'] for chunk in chunks]
    metadatas = [
        {'source': file.filename, 'chunk_num': i, **chunk['metadata']}
        for i, chunk in enumerate(chunks)
    ]
    ids = [_chunk_id(file.filename, i) for i in range(len(chunks))]

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: Chroma.collection.upsert(documents=documents, metadatas=metadatas, ids=ids),
        )
    except Exception:
        logger.exception("Failed to upsert chunks into ChromaDB: %s", file.filename)
        raise HTTPException(status_code=500, detail="Failed to index document")

    try:
        _save(file.filename, file_content)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to save file to disk: %s", file.filename)
        raise HTTPException(status_code=500, detail="Failed to save file")

    return {
        "status": "success",
        "chunks_created": len(chunks),
        "sample_chunk": {
            "text": chunks[0]['text'][:500] + "...",
            "length": len(chunks[0]['text']),
        },
    }
