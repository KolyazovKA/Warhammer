import logging
import os

logger = logging.getLogger(__name__)


class Config:
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_EMBED_URL = "https://api.deepseek.com/v1/embeddings"
    DEEPSEEK_TEMPERATURE: float = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.8"))
    LOG_LEVEL = "info"
    EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "deepseek")
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8081")

    @classmethod
    def validate(cls) -> None:
        if not cls.DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY environment variable is not set. Create a .env file.")
        if cls.EMBEDDING_BACKEND not in ("deepseek", "gte-small"):
            raise RuntimeError(f"Unknown EMBEDDING_BACKEND: {cls.EMBEDDING_BACKEND!r}. Use 'deepseek' or 'gte-small'.")
