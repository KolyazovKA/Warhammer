from ..deps import collection

def add_document(doc_id: str, text: str):
    collection.add(documents=[text], ids=[doc_id])

def search(query: str, n_results: int = 3):
    results = collection.query(query_texts=[query], n_results=n_results)
    return results["documents"][0]
