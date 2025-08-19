from chromadb import PersistentClient
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from .config import CHROMA_DIR

# локальная модель
model = SentenceTransformer("thenlper/gte-small")

class LocalEmbeddingFunction(embedding_functions.EmbeddingFunction):
    def __call__(self, texts: list[str]) -> list[list[float]]:
        return model.encode(texts, convert_to_numpy=True).tolist()

# persistent client
client = PersistentClient(path=CHROMA_DIR)

# эмбеддер на основе gte-small
embedding_func = LocalEmbeddingFunction()

# коллекция
collection = client.get_or_create_collection(
    "my_docs",
    embedding_function=embedding_func
)
