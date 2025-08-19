from chromadb import PersistentClient

from embeddings.function import embedding_func


class Chroma:
    client = None
    collection = None

    @staticmethod
    def initialize():
        Chroma.client = PersistentClient(path="choma_db")
        Chroma.collection = Chroma.client.get_or_create_collection(
            name="choma_collection",
            embedding_function=embedding_func,
        )
