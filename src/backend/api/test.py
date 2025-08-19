from fastapi import APIRouter

router = APIRouter()
@router.get("/test")
async def debug_function_1():
    return {"text": "text"}
