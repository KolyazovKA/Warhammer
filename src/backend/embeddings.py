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
