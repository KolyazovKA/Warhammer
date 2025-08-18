from typing import List, Tuple, Dict
import re
from datetime import datetime


def split_text_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[Dict]:
    """
    Split text into chunks with metadata including page numbers and dates.

    Args:
        text: The full text to split
        chunk_size: Maximum size of each chunk in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        List of dictionaries with 'text' and 'metadata' for each chunk
    """
    chunks = []
    start = 0
    length = len(text)

    # Extract page numbers if they exist in the text
    page_numbers = []
    page_matches = list(re.finditer(r'(?:\n|\f)page\s*(\d+)(?:\n|\f)', text.lower()))
    for i, match in enumerate(page_matches):
        page_num = int(match.group(1))
        start_pos = match.start()
        end_pos = match.end()
        if i < len(page_matches) - 1:
            end_pos = page_matches[i + 1].start()
        page_numbers.append((start_pos, end_pos, page_num))

    # Extract dates
    date_pattern = r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b'
    dates = []
    for match in re.finditer(date_pattern, text):
        dates.append((match.start(), match.end(), match.group()))

    while start < length:
        end = min(start + chunk_size, length)
        chunk_text = text[start:end]

        # Find metadata for this chunk
        metadata = {
            'start_pos': start,
            'end_pos': end,
            'pages': [],
            'dates': []
        }

        # Add page numbers
        for page_start, page_end, page_num in page_numbers:
            if start <= page_start < end or start <= page_end < end:
                metadata['pages'].append(page_num)

        # Add dates
        for date_start, date_end, date_str in dates:
            if start <= date_start < end or start <= date_end < end:
                try:
                    parsed_date = datetime.strptime(date_str, '%m/%d/%Y').strftime('%Y-%m-%d')
                except ValueError:
                    try:
                        parsed_date = datetime.strptime(date_str, '%d-%m-%Y').strftime('%Y-%m-%d')
                    except ValueError:
                        parsed_date = date_str  # fallback to original if parsing fails
                metadata['dates'].append(parsed_date)

        # Remove duplicates
        metadata['pages'] = list(sorted(set(metadata['pages'])))
        metadata['dates'] = list(sorted(set(metadata['dates'])))

        chunks.append({
            'text': chunk_text,
            'metadata': metadata
        })

        # Move to next chunk with overlap
        if end == length:
            break
        start = end - overlap

    return chunks
