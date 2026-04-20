from pathlib import Path

from chromadb import PersistentClient

from embeddings.function import embedding_func

_DB_PATH = Path(__file__).parent.parent / "choma_db"


class Chroma:
    client = None
    collection = None

    @staticmethod
    def initialize():
        Chroma.client = PersistentClient(path=str(_DB_PATH))
        Chroma.collection = Chroma.client.get_or_create_collection(
            name="choma_collection",
            embedding_function=embedding_func,
        )
