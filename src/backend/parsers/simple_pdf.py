import io

from PyPDF2 import PdfReader

from util import clean_text


async def extract_text_from_pdf(file) -> str:
    """Extract text from PDFs with text layers only (no OCR)"""
    pdf_content = await file.read()
    full_text = ""

    # Option A: Using pypdf (most lightweight)
    reader = PdfReader(io.BytesIO(pdf_content))
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = clean_text(text)
        if text:
            full_text += f"\nPAGE {page_num}\n{text}\n"

    return full_text