import uvicorn
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import shutil
from typing import Dict
from chromadb import PersistentClient
from urllib.parse import quote
from starlette.middleware.cors import CORSMiddleware

from config import Config
from persistence.chroma import Chroma

os.environ.update({"DEEPSEEK_API_KEY": "sk-011533b41d13463d98a3e558896665b8"})

app = FastAPI(title="DeepSeek RAG over Choma")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from api.chat.semantics import router as chat_router
from api.documents.upload import router as upload_router

app.include_router(chat_router)
app.include_router(upload_router)
# Монтируем статическую директорию для доступа к файлам
app.mount("/files", StaticFiles(directory="src/backend/files"), name="files")

class Query(BaseModel):
    question: str

@app.post("/search")
async def search_chroma(query: Query):
    text_only_search_results = Chroma.collection.get(
        where_document={"$contains": query.question},
    )
    return text_only_search_results

@app.get("/get_books")
async def get_books() -> Dict[str, str]:
    # Путь к целевой папке
    folder_path = 'src/backend/files'
    
    # Проверяем существование папки
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Собираем список файлов (игнорируем директории)
    files = {}
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            # Кодируем имя файла для URL
            encoded_filename = quote(filename)
            files[filename] = f"http://localhost:8081/files/{encoded_filename}"
    
    return JSONResponse(content=files)

if __name__ == "__main__":
    Chroma.initialize()
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,
        log_level=Config.LOG_LEVEL,
    )