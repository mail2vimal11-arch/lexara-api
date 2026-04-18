"""File upload endpoint — extracts text from PDF, DOCX, or TXT."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel
import io
import logging

from app.security import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}


class UploadResponse(BaseModel):
    filename: str
    content_type: str
    text: str
    char_count: int
    word_count: int


@router.post("/upload", response_model=UploadResponse)
async def upload_contract(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """
    Upload a contract file (PDF, DOCX, TXT) and extract its text.
    Returns the extracted text ready to pass into analysis endpoints.
    Max size: 10MB.
    """
    # Read file
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")

    content_type = file.content_type or ""
    filename = file.filename or "unknown"

    try:
        text = await extract_text(content, content_type, filename)
    except Exception as e:
        logger.error(f"Text extraction failed: {e}", exc_info=True)
        raise HTTPException(status_code=422, detail=f"Could not extract text from file: {str(e)}")

    text = text.strip()
    if len(text) < 50:
        raise HTTPException(status_code=422, detail="Could not extract readable text from this file.")

    return UploadResponse(
        filename=filename,
        content_type=content_type,
        text=text,
        char_count=len(text),
        word_count=len(text.split()),
    )


async def extract_text(content: bytes, content_type: str, filename: str) -> str:
    """Extract plain text from PDF, DOCX, or TXT."""

    fn_lower = filename.lower()

    # PDF
    if content_type == "application/pdf" or fn_lower.endswith(".pdf"):
        return extract_pdf(content)

    # DOCX
    if (content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            or fn_lower.endswith(".docx")):
        return extract_docx(content)

    # DOC (legacy — treat as plain text fallback)
    if content_type == "application/msword" or fn_lower.endswith(".doc"):
        raise HTTPException(status_code=422, detail="Legacy .doc format not supported. Please save as .docx or .pdf.")

    # Plain text
    if content_type.startswith("text/") or fn_lower.endswith(".txt"):
        return content.decode("utf-8", errors="replace")

    # Try plain text as fallback
    try:
        return content.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=422, detail="Unsupported file type. Please upload PDF, DOCX, or TXT.")


def extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        t = page.extract_text()
        if t:
            pages.append(t)
    return "\n\n".join(pages)


def extract_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
