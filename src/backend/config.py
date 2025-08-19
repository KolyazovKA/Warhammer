import os

class Config:
    """
    Класс конфигурации
    """
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    DEEPSEEK_EMBED_URL = "https://api.deepseek.com/v1/embeddings"
    DEEPSEEK_TEMPERATURE = 0.8
    LOG_LEVEL = "info"

