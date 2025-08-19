from main import app


@app.get("/test")
async def debug_function_1():
    return {"text": "text"}
