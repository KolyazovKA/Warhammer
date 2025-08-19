from fastapi import UploadFile, File, HTTPException, APIRouter

from parsers.docx_parser import extract_text_from_docx
from parsers.fb2 import extract_text_from_fb2
from parsers.simple_pdf import extract_text_from_pdf
from util import smart_chunking


router = APIRouter()
@router.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        file_extension = file.filename.split('.')[-1].lower()

        if file_extension == 'pdf':
            full_text = extract_text_from_pdf(file_content)
        elif file_extension == 'fb2':
            full_text = extract_text_from_fb2(file_content)
        elif file_extension == 'epub':
            full_text = extract_text_from_epub(file_content)
        elif file_extension == 'doc' or file_extension == 'docx':
            full_text = extract_text_from_docx(file_content)
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file format. Supported formats: PDF, FB2, EPUB"
            )

        # Split into meaningful chunks (using your existing function)
        chunks = smart_chunking(full_text)

        # Prepare for ChromaDB
        documents = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            documents.append(chunk['text'])
            metadatas.append({
                'source': str(file.filename),
                'chunk_num': int(i),
                **chunk['metadata']
            })
            ids.append(f"{file.filename}_chunk_{i}")

        # Store in ChromaDB
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

        return {
            "status": "success",
            "chunks_created": len(chunks),
            "sample_chunk": {
                "text": chunks[0]['text'][:500] + "..." if chunks else None,
                "length": len(chunks[0]['text']) if chunks else 0
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )