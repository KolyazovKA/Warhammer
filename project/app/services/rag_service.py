from . import chroma_service, llm_service

def ask(question: str) -> str:
    # 1. поиск в ChromaDB
    docs = chroma_service.search(question, n_results=3)
    context = "\n".join(docs)

    # 2. формируем промпт
    prompt = f"{question}\n\nТебе нужно использовать только следующую информацию:\n{context}"

    # 3. отправляем промпт в модель
    return llm_service.ask_deepseek(prompt)
