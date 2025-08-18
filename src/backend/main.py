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
    # 1. Поиск в ChromaDB
    results = collection.query(query_texts=[query.question], n_results=3)
    context_chunks = results.get("documents", [[]])[0]
    context_text = "\n\n".join(context_chunks)

    # 2. Формируем prompt
    prompt = f"""
Ты ассистент, отвечающий только на основе базы Choma.
Вот найденная информация:
{context_text}

Вопрос: {query.question}
Если ответа нет в информации выше, скажи "Не найдено в базе Choma".
"""
# Если ответ есть, выведи релевантные куски текста.

    # 3. Запрос к DeepSeek
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ты помощник для поиска по базе Choma"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
    try:
        resp.raise_for_status()
    except Exception as e:
        print(e)
    answer = resp.json()["choices"][0]["message"]["content"]

    return {"answer": answer, "context_used": context_chunks}


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    # Save PDF temporarily
    with open("temp.pdf", "wb") as f:
        f.write(await file.read())

    # Extract text using PyPDF2
    reader = PdfReader("temp.pdf")
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    # Store in ChromaDB (for RAG later)
    collection.add(
        documents=[text],
        ids=[file.filename]  # Unique ID for each doc
    )

    return {"status": "success", "text": text[:200] + "..."}  # Preview first 200 chars


if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,
        log_level=Config.LOG_LEVEL,
    )