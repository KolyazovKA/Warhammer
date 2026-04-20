import re
from typing import List, Dict


def clean_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    text = re.sub(r'(?<=\w)-\s+(?=\w)', '', text)
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    return text


def smart_chunking(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
    """Split text into sentence-boundary-respecting chunks with date and page metadata."""
    date_pattern = (
        r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}'
        r'|\d{4}[-/]\d{1,2}[-/]\d{1,2}'
        r'|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b'
    )

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk: List[str] = []
    current_length = 0

    def _flush(sentences_list: List[str]) -> Dict:
        chunk_text = ' '.join(sentences_list)
        dates = sorted(set(re.findall(date_pattern, chunk_text)))
        pages = sorted({int(m) for m in re.findall(r'PAGE (\d+)', chunk_text)})
        return {
            'text': chunk_text,
            'metadata': {'chunk_type': 'natural_break', 'dates': dates, 'pages': pages},
        }

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_length = len(sentence)

        if current_chunk and current_length + sentence_length > chunk_size:
            chunks.append(_flush(current_chunk))
            if overlap:
                overlap_sentences: List[str] = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) > overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s)
                current_chunk = overlap_sentences
                current_length = overlap_len
            else:
                current_chunk = []
                current_length = 0

        current_chunk.append(sentence)
        current_length += sentence_length

    if current_chunk:
        chunks.append(_flush(current_chunk))

    return chunks
