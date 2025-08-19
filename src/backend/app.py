# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Добавляем CORS, чтобы фронтенд мог обращаться с другого порта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # в проде лучше указать конкретный фронтенд
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/test")
async def read_test():
    return "test"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
