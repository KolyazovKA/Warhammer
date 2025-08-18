#!/bin/sh

# main.py
cat > project/app/main.py << 'EOF'
from fastapi import FastAPI
from .routes import rag

app = FastAPI(title="DeepSeek + Chroma RAG API")
app.include_router(rag.router, prefix="/api")
EOF

# config.py
cat > project/app/config.py << 'EOF'
import os

DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")
EOF

# deps.py
cat > project/app/deps.py << 'EOF'
from chromadb import Client
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from .config import CHROMA_DIR, DEEPSEEK_KEY

client = Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=CHROMA_DIR))
embedding_func = embedding_functions.OpenAIEmbeddingFunction(
    api_key=DEEPSEEK_KEY,
    model_name="text-embedding-ada-002"  # замените на deepseek-embedding при необходимости
)
collection = client.get_or_create_collection("my_docs", embedding_function=embedding_func)
EOF

# models/query.py
cat > project/app/models/query.py << 'EOF'
from pydantic import BaseModel

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
EOF

# services/chroma_service.py
cat > project/app/services/chroma_service.py << 'EOF'
from ..deps import collection

def add_document(doc_id: str, text: str):
    collection.add(documents=[text], ids=[doc_id])

def search(query: str, n_results: int = 3):
    results = collection.query(query_texts=[query], n_results=n_results)
    return results["documents"][0]
EOF

# services/llm_service.py
cat > project/app/services/llm_service.py << 'EOF'
import requests
from ..config import DEEPSEEK_KEY

def ask_deepseek(prompt: str) -> str:
    headers = {"Authorization": f"Bearer {DEEPSEEK_KEY}"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ты отвечаешь только на основе предоставленного контекста."},
            {"role": "user", "content": prompt}
        ]
    }
    r = requests.post("https://api.deepseek.com/chat/completions", json=payload, headers=headers)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
EOF

# services/rag_service.py
cat > project/app/services/rag_service.py << 'EOF'
from . import chroma_service, llm_service

def ask(query: str) -> str:
    context_docs = chroma_service.search(query, n_results=3)
    context = "\n".join(context_docs)
    prompt = f"Контекст:\n{context}\n\nВопрос: {query}"
    return llm_service.ask_deepseek(prompt)
EOF

# routes/rag.py
cat > project/app/routes/rag.py << 'EOF'
from fastapi import APIRouter
from ..models.query import QueryRequest, QueryResponse
from ..services.rag_service import ask

router = APIRouter()

@router.post("/ask", response_model=QueryResponse)
def ask_endpoint(request: QueryRequest):
    answer = ask(request.query)
    return QueryResponse(answer=answer)
EOF

# routes/__init__.py
cat > project/app/routes/__init__.py << 'EOF'
# Маршруты FastAPI
EOF

# requirements.txt
cat > project/requirements.txt << 'EOF'
fastapi
uvicorn
chromadb
requests
pydantic
EOF

# Dockerfile
cat > project/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

# README.md
cat > project/README.md << 'EOF'
# DeepSeek + Chroma RAG

## Запуск локально

```bash

