import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote
from typing import Dict

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

load_dotenv()

from config import Config
from persistence.chroma import Chroma

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_FILES_DIR = Path(__file__).parent / "files"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Config.validate()
    Chroma.initialize()
    _FILES_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("ChromaDB initialized. Files directory: %s", _FILES_DIR)
    async with httpx.AsyncClient(timeout=60.0) as client:
        app.state.http_client = client
        yield


app = FastAPI(title="DeepSeek RAG over Choma", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:8082"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

from api.chat.semantics import router as chat_router
from api.documents.upload import router as upload_router

app.include_router(chat_router)
app.include_router(upload_router)

app.mount("/files", StaticFiles(directory=str(_FILES_DIR)), name="files")


@app.get("/get_books")
async def get_books() -> Dict[str, str]:
    if not _FILES_DIR.exists():
        raise HTTPException(status_code=404, detail="Files folder not found")

    files = {
        filename: f"{Config.BASE_URL}/files/{quote(filename)}"
        for filename in os.listdir(_FILES_DIR)
        if (_FILES_DIR / filename).is_file()
    }
    return JSONResponse(content=files)


if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,
        log_level=Config.LOG_LEVEL,
    )
