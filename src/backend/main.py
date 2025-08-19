import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import os
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

class Query(BaseModel):
    question: str

@app.post("/search")
async def search_chroma(query: Query):
    text_only_search_results = Chroma.collection.get(
        where_document={"$contains": query.question},
    )
    return text_only_search_results



if __name__ == "__main__":
    Chroma.initialize()
    uvicorn.run(
        app="main:app",
        host="0.0.0.0",
        port=8081,
        log_level=Config.LOG_LEVEL,
    )