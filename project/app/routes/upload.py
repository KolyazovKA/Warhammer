from fastapi import APIRouter, UploadFile, File
import shutil
import uuid
import os
from ..services import file_loader, chroma_service

router = APIRouter()

UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1]
    temp_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")

    # сохраняем
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # извлекаем текст
    text = file_loader.load_file_text(temp_path)

    # добавляем в Chroma
    chroma_service.add_document(doc_id=str(uuid.uuid4()), text=text)

    return {"filename": file.filename, "stored_as": temp_path, "status": "added to DB"}
