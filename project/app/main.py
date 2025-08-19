from fastapi import FastAPI
from .routes import rag, upload

app = FastAPI(title="DeepSeek + Chroma RAG API")
app.include_router(rag.router)
app.include_router(upload.router, prefix="/api")
