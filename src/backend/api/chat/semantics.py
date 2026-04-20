import asyncio
import logging

import httpx
from fastapi import HTTPException, APIRouter, Request
from pydantic import BaseModel

from config import Config
from persistence.chroma import Chroma
from schemas.semantic_response import SemanticsResponseSchema

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_QUESTION_LEN = 2000


class Query(BaseModel):
    question: str


@router.post("/api/chat/semantics", response_model=SemanticsResponseSchema)
async def ask_choma(query: Query, request: Request):
    if len(query.question) > _MAX_QUESTION_LEN:
        raise HTTPException(status_code=400, detail=f"Question too long (max {_MAX_QUESTION_LEN} characters)")

    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(
        None,
        lambda: Chroma.collection.query(query_texts=[query.question], n_results=15),
    )

    docs = results.get('documents') or []
    metas = results.get('metadatas') or []
    if not docs or not docs[0]:
        return {"answer": "Не найдено в базе Chroma", "sources": []}

    context_chunks = []
    for chunk_text, metadata in zip(docs[0], metas[0]):
        if metadata is None:
            continue
        source_info = f"Source: {metadata['source']}"
        page_info = (
            f"Pages: {', '.join(map(str, metadata['pages']))}"
            if metadata.get('pages') else ""
        )
        date_info = (
            f"Dates: {', '.join(metadata['dates'])}"
            if metadata.get('dates') else ""
        )
        context_chunks.append(f"{chunk_text}\n\n{source_info}\n{page_info}\n{date_info}")

    context_text = "\n\n---\n\n".join(context_chunks)

    prompt = (
        "Ты ассистент, отвечающий только на основе базы Chroma.\n"
        "Вот найденная информация с метаданными (источник, страницы, даты):\n"
        f"{context_text}\n\n"
        "---\n"
        f"Вопрос пользователя: {query.question}\n\n"
        'Если ответа нет в информации выше, скажи "Не найдено в базе Chroma".\n'
        "Если отвечаешь, укажи источник и страницы, откуда взята информация."
    )

    headers = {
        "Authorization": f"Bearer {Config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": "Ты помощник для поиска по базе Chroma. Всегда указывай источник информации.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": Config.DEEPSEEK_TEMPERATURE,
    }

    http_client: httpx.AsyncClient = request.app.state.http_client
    try:
        resp = await http_client.post(Config.DEEPSEEK_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error("DeepSeek API HTTP error %s: %s", e.response.status_code, e.response.text)
        raise HTTPException(status_code=502, detail=f"DeepSeek API error: {e.response.status_code}")
    except httpx.RequestError as e:
        logger.exception("DeepSeek API request failed")
        raise HTTPException(status_code=502, detail=f"DeepSeek API unreachable: {str(e)}")

    try:
        answer = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        logger.error("Unexpected DeepSeek response structure: %s", resp.text[:500])
        raise HTTPException(status_code=502, detail="Unexpected response from DeepSeek API")

    return {
        "answer": answer,
        "sources": [
            {"text": text, "metadata": meta}
            for text, meta in zip(docs[0], metas[0])
        ],
    }
