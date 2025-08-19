import requests
from fastapi import HTTPException, APIRouter
from pydantic import BaseModel

from config import Config
from persistence.chroma import Chroma

"""
POST /api/documents/upload – загрузка документов

POST /api/chat/keywords – запрос по ключевым словам;

POST /api/chat/semantics – семантический поиск.
"""


class Query(BaseModel):
    question: str

router = APIRouter()
@router.post("/api/chat/semantics")
async def ask_choma(query: Query):
    """

    Args:
        query:

    Returns:

    """
    # 1. Search in ChromaDB with metadata filtering if needed
    results = Chroma.collection.query(
        query_texts=[query.question],
        n_results=15,
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
    headers = {"Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system",
             "content": "Ты помощник для поиска по базе Chroma. Всегда указывай источник информации."},
            {"role": "user", "content": prompt}
        ],
        "temperature": Config.DEEPSEEK_TEMPERATURE
    }

    resp = requests.post(Config.DEEPSEEK_API_URL, headers=headers, json=payload)
    try:
        resp.raise_for_status()
    except Exception as e:
        print(e)
        print(resp)
        raise HTTPException(
            status_code=400,
            detail=f"""Failed to query DeepSeek API: {str(e)}
Response: {str(resp)}
"""
        )

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