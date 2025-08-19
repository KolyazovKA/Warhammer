import io

import docx


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX (Microsoft Word) format."""
    try:
        docx_file = io.BytesIO(file_content)
        doc = docx.Document(docx_file)
        result = []
        for para in doc.paragraphs:
            result.append(para.text)
        return '\n'.join(result)
    except Exception as e:
        raise ValueError(f"Failed to parse DOC(X) file: {str(e)}")
