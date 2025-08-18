import sys

import uvicorn
from PyPDF2 import PdfReader
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
import requests
import os
from chromadb import PersistentClient
from starlette.middleware.cors import CORSMiddleware

from config import Config
from embeddings import DeepSeekEmbeddingFunction, GTESmallEmbeddingFunction
from util import split_text_into_chunks, extract_text_from_pdf, smart_chunking

os.environ.update({"DEEPSEEK_API_KEY": "sk-011533b41d13463d98a3e558896665b8"})

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

app = FastAPI(title="DeepSeek RAG over Choma")

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)



# ChromaDB
client = PersistentClient(path="choma_db")

#gte_embedder = GTESmallEmbeddingFunction()
embedding_func = DeepSeekEmbeddingFunction(api_key=DEEPSEEK_API_KEY)
# collection = client.get_or_create_collection(
#     name="gte_collection",
#     embedding_function=gte_embedder
# )
collection = client.get_or_create_collection(
    name="choma_collection",
    embedding_function=embedding_func,
)
class Query(BaseModel):
    question: str

@app.get("/test")
async def wtest():
    return {"text": "text"}


@app.post("/ask")
async def ask_choma(query: Query):
    # 1. Search in ChromaDB with metadata filtering if needed
    results = collection.query(
        query_texts=[query.question],
        n_results=15,
        # You can add metadata filters here if needed
        # where={"metadata_field": {"$eq": "value"}}
    )

    # Prepare context with metadata
    context_chunks = []
    for i in range(len(results['documents'][0])):
        chunk_text = results['documents'][0][i]
        metadata = results['metadatas'][0][i]
        if metadata is None:
            continue

        # Format metadata for display
        source_info = f"Source: {metadata['source']}"
        page_info = f"Pages: {', '.join(map(str, metadata['pages']))}" if 'pages' in metadata else ""
        date_info = f"Dates: {', '.join(metadata['dates'])}" if 'dates' in metadata else ""

        context_chunks.append(
        f"{chunk_text}\n\n{source_info}\n{page_info}\n{date_info}"
        )

    context_text = "\n\n---\n\n".join(context_chunks)

        # 2. Form the prompt
    prompt = f"""
Ты ассистент, отвечающий только на основе базы Chroma.
Вот найденная информация с метаданными (источник, страницы, даты):
{context_text}

Вопрос: {query.question}

Если ответа нет в информации выше, скажи "Не найдено в базе Chroma".
Если отвечаешь, укажи источник и страницы, откуда взята информация.
"""

    # 3. Query DeepSeek
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system",
             "content": "Ты помощник для поиска по базе Chroma. Всегда указывай источник информации."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.8
    }

    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
    try:
        resp.raise_for_status()
    except Exception as e:
        print(e)
        print(resp)
        return {"error": "Failed to query DeepSeek API"}

    answer = resp.json()["choices"][0]["message"]["content"]



    return {
        "answer": answer,
        "sources": [
            {
                "text": results['documents'][0][i],
                "metadata": results['metadatas'][0][i]
            } for i in range(len(results['documents'][0]))
        ]
    }


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        # Extract and clean text
        full_text = await extract_text_from_pdf(file)

        # Split into meaningful chunks
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
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,
        log_level=Config.LOG_LEVEL,
    )