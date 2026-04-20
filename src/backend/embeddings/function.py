from config import Config
from embeddings.deepseek import DeepSeekEmbeddingFunction
from embeddings.gte_small import GTESmallEmbeddingFunction

if Config.EMBEDDING_BACKEND == "gte-small":
    embedding_func = GTESmallEmbeddingFunction()
else:
    embedding_func = DeepSeekEmbeddingFunction(api_key=Config.DEEPSEEK_API_KEY)
