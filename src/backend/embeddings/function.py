from config import Config
from embeddings.deepseek import DeepSeekEmbeddingFunction

embedding_func = DeepSeekEmbeddingFunction(api_key=Config.DEEPSEEK_API_KEY)