from typing import List

from chromadb.utils import embedding_functions


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
