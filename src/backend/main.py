import sys

import uvicorn
from PyPDF2 import PdfReader
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
import requests
import os
from chromadb import PersistentClient


from config import Config
from embeddings import DeepSeekEmbeddingFunction
from util import split_text_into_chunks

os.environ.update({"DEEPSEEK_API_KEY": "sk-011533b41d13463d98a3e558896665b8"})

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

app = FastAPI(title="DeepSeek RAG over Choma")

# ChromaDB
client = PersistentClient(path="choma_db")
embedding_func = DeepSeekEmbeddingFunction(api_key=DEEPSEEK_API_KEY)
collection = client.get_or_create_collection(
    name="choma_collection",
    embedding_function=embedding_func
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
        n_results=3,
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
        page_info = f"Pages: {', '.join(map(str, metadata['pages']))}" if metadata['pages'] else ""
        date_info = f"Dates: {', '.join(metadata['dates'])}" if metadata['dates'] else ""

        context_chunks.append(
        f"{chunk_text}\n\n{source_info}\n{page_info}\n{date_info}"
        )

    context_text = "\n\n---\n\n".join(context_chunks)

        # 2. Form the prompt
    prompt = f"""
Ты ассистент, отвечающий только на основе базы Choma.
Вот найденная информация с метаданными (источник, страницы, даты):
{context_text}

Вопрос: {query.question}

Если ответа нет в информации выше, скажи "Не найдено в базе Choma".
Если отвечаешь, укажи источник и страницы, откуда взята информация.
"""

    # 3. Query DeepSeek
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system",
             "content": "Ты помощник для поиска по базе Choma. Всегда указывай источник информации."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
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
    # Save PDF temporarily
    with open("temp.pdf", "wb") as f:
        f.write(await file.read())

    # Extract text using PyPDF2
    reader = PdfReader("temp.pdf")
    full_text = ""
    page_texts = []

    for page_num, page in enumerate(reader.pages, start=1):
        page_content = page.extract_text() or ""
        # Add page number marker
        page_content = f"\nPAGE {page_num}\n{page_content}"
        page_texts.append(page_content)
        full_text += page_content + "\n"

    # Split into chunks with metadata
    chunks = split_text_into_chunks(full_text)

    # Prepare documents and metadata for ChromaDB
    documents = []
    metadatas = []
    ids = []

    for i, chunk in enumerate(chunks):
        documents.append(chunk['text'])

        # Convert metadata to ChromaDB-compatible format
        pages_str = ",".join(map(str, chunk['metadata']['pages'])) if chunk['metadata']['pages'] else ""
        dates_str = ",".join(chunk['metadata']['dates']) if chunk['metadata']['dates'] else ""

        metadatas.append({
            'source': str(file.filename),
            'pages': str(pages_str),  # Ensure string type
            'dates': str(dates_str),  # Ensure string type
            'chunk_num': int(i)  # Ensure integer type
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
        "sample_chunk": chunks[0] if chunks else None
    }


if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,
        log_level=Config.LOG_LEVEL,
    )