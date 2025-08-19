from chromadb.utils import embedding_functions
import requests

from config import Config


class DeepSeekEmbeddingFunction(embedding_functions.DefaultEmbeddingFunction):
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key

    def __call__(self, texts):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"input": texts, "model": "deepseek-embedding"}
        resp = requests.post(Config.DEEPSEEK_EMBED_URL, headers=headers, json=payload)
        resp.raise_for_status()
        embeddings = [item["embedding"] for item in resp.json()["data"]]
        return embeddings

