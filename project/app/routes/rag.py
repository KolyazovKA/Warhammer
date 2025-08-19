from fastapi import APIRouter
from ..services.rag_service import ask
from ..models.query import QueryRequest

router = APIRouter(prefix="/api")

@router.post("/ask")
def ask_endpoint(request: QueryRequest):
    return {"answer": ask(request.query)}
