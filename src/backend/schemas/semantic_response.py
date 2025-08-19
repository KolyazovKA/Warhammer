from pydantic import BaseModel

#     "answer": answer,
#     "sources": [
#         {
#             "text": results['documents'][0][i],
#             "metadata": results['metadatas'][0][i]
#         } for i in range(len(results['documents'][0]))
#     ]

class TextSourceItem:
    text: str
    metadata: dict


class SemanticsResponseSchema(BaseModel):
    answer: str
    sources: list[TextSourceItem]
