import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import os
from chromadb import PersistentClient
from starlette.middleware.cors import CORSMiddleware

from config import Config
from embeddings.deepseek import DeepSeekEmbeddingFunction

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


# ChromaDB
client = PersistentClient(path="choma_db")

embedding_func = DeepSeekEmbeddingFunction(api_key=Config.DEEPSEEK_API_KEY)

collection = client.get_or_create_collection(
    name="choma_collection",
    embedding_function=embedding_func,
)
class Query(BaseModel):
    question: str


@app.post("/search")
async def search_chroma(query: Query):
    text_only_search_results = collection.get(
        where_document={"$contains": query.question},
    )
    return text_only_search_results



if __name__ == "__main__":
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,
        log_level=Config.LOG_LEVEL,
    )