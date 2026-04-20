from pydantic import BaseModel


class TextSourceItem(BaseModel):
    text: str
    metadata: dict


class SemanticsResponseSchema(BaseModel):
    answer: str
    sources: list[TextSourceItem]
