from typing import List

from chromadb.utils import embedding_functions
import requests
import os

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_EMBED_URL = "https://api.deepseek.com/v1/embeddings"

class DeepSeekEmbeddingFunction(embedding_functions.DefaultEmbeddingFunction):
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key

    def __call__(self, texts):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"input": texts, "model": "deepseek-embedding"}
        resp = requests.post(DEEPSEEK_EMBED_URL, headers=headers, json=payload)
        resp.raise_for_status()
        embeddings = [item["embedding"] for item in resp.json()["data"]]
        return embeddings



class GTESmallEmbeddingFunction(embedding_functions.DefaultEmbeddingFunction):
    def __init__(self, model_name: str = "gte-small"):
        super().__init__()
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("thenlper/gte-small")
            # Warm up the model
            self.model.encode("warmup")
        except ImportError:
            raise ImportError(
                "The sentence-transformers package is required for GTESmallEmbeddingFunction. "
                "Please install it with: pip install sentence-transformers"
            )

    def __call__(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

# Alternatively, if you want a HuggingFace API version (remote)
class GTESmallHuggingFaceEmbeddingFunction(embedding_functions.DefaultEmbeddingFunction):
    def __init__(self, api_key: str = None):
        super().__init__()
        self.api_key = api_key or os.getenv("HF_API_KEY")
        self.api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/gte-small"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def __call__(self, texts: List[str]) -> List[List[float]]:
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json={"inputs": texts, "options": {"wait_for_model": True}}
        )
        response.raise_for_status()
        return response.json()
