import io
import os
from typing import List, Tuple, Dict
import re
from datetime import datetime
import docx
import ebooklib

import pdfplumber
from PyPDF2 import PdfReader
from fastapi import UploadFile

from ebooklib import epub
from bs4 import BeautifulSoup
import zipfile
import xml.etree.ElementTree as ET


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


def clean_text(text: str) -> str:
    """Clean extracted text by removing excessive whitespace and formatting artifacts"""
    # Normalize all whitespace sequences to single spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing whitespace
    text = text.strip()
    # Fix common PDF extraction artifacts
    text = re.sub(r'(?<=\w)-\s+(?=\w)', '', text)  # Join hyphenated words
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)  # Fix punctuation spacing
    return text


def smart_chunking(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict]:
    """Split text into meaningful chunks respecting sentence boundaries"""
    sentences = re.split(r'(?<=[.!?])\s+', text)  # Split on sentence boundaries
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        sentence_length = len(sentence)

        # If adding this sentence would exceed chunk size (with some tolerance)
        if current_chunk and current_length + sentence_length > chunk_size:
            chunks.append({
                'text': ' '.join(current_chunk),
                'metadata': {'chunk_type': 'natural_break'}
            })
            # Keep overlap sentences for context
            current_chunk = current_chunk[-overlap // 50:] if overlap else []
            current_length = sum(len(s) for s in current_chunk)

        current_chunk.append(sentence)
        current_length += sentence_length

    # Add the last chunk if it has content
    if current_chunk:
        chunks.append({
            'text': ' '.join(current_chunk),
            'metadata': {'chunk_type': 'natural_break'}
        })

    return chunks


# import re
#
# def clean_text(text: str) -> str:
#     # Убираем лишние пробелы и переносы строк внутри абзацев
#     text = re.sub(r'[ \t]+', ' ', text)  # лишние пробелы
#     text = re.sub(r'\n+', '\n', text)    # несколько переносов в один
#     text = text.strip()
#     return text
#
# def split_into_segments(text: str, max_chars: int = 1000):
#     segments = []
#     current = ""
#     for line in text.split('\n'):
#         if len(current) + len(line) > max_chars:
#             segments.append(current.strip())
#             current = ""
#         current += line + ' '
#     if current:
#         segments.append(current.strip())
#     return segments


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDFs with text layers only (no OCR)"""
    full_text = ""

    # Option A: Using pypdf (most lightweight)
    reader = PdfReader(io.BytesIO(file_content))
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = clean_text(text)
        if text:
            full_text += f"\nPAGE {page_num}\n{text}\n"

    return full_text


def extract_text_from_fb2(file_content: bytes) -> str:
    """Extract text from FB2 (FictionBook) format."""
    try:
        root = ET.fromstring(file_content)
        # FB2 namespace might be present
        ns = {'fb2': 'http://www.gribuser.ru/xml/fictionbook/2.0'}

        # Find all text sections
        bodies = root.findall('.//fb2:body', ns) or root.findall('.//body')
        text_parts = []

        for body in bodies:
            # Extract all paragraphs
            paragraphs = body.findall('.//fb2:p', ns) or body.findall('.//p')
            for p in paragraphs:
                if p.text:
                    text_parts.append(p.text)
                # Handle mixed content
                text_parts.append(''.join(p.itertext()))

        return '\n\n'.join(text_parts)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse FB2 file: {str(e)}")


def extract_text_from_epub(file_content: bytes) -> str:
    """Extract text from EPUB format."""
    try:
        # EPUB is essentially a zip file with XHTML content
        with zipfile.ZipFile(io.BytesIO(file_content)) as z:
            # Parse the container to find the root file
            with z.open('META-INF/container.xml') as container_file:
                container = ET.fromstring(container_file.read())
                rootfile_path = container.find(
                    './/{urn:oasis:names:tc:opendocument:xmlns:container}rootfile'
                ).attrib['full-path']

            # Parse the root file to find all documents
            with z.open(rootfile_path) as root_file:
                #root_content = root_file.read()
                result = ""
                soup = BeautifulSoup(root_file.read(), 'lxml')
                for text_object in soup.find_all(text=True):
                    result += "\n" + text_object.text

                return result
    except Exception as e:
        raise ValueError(f"Failed to parse EPUB file: {str(e)}")


def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX (Microsoft Word) format."""
    try:
        docx_file = io.BytesIO(file_content)
        doc = docx.Document(docx_file)
        result = []
        for para in doc.paragraphs:
            result.append(para.text)
        return '\n'.join(result)
    except Exception as e:
        raise ValueError(f"Failed to parse DOC(X) file: {str(e)}")


def extract_epub_text_with_metadata(file_content: bytes, output_folder=None):
    """
    Extract text and metadata from an EPUB file.

    Args:
        epub_path (str): Path to the EPUB file
        output_folder (str, optional): Folder to save extracted text. If None, returns as dict.

    Returns:
        dict or None: If output_folder is None, returns dictionary with text and metadata.
                      Otherwise saves files and returns None.
    """
    # Read the EPUB file
    book = epub.read_epub(io.BytesIO(file_content))

    # Initialize result dictionary
    result = {
        'book_title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Untitled',
        'author': book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else 'Unknown',
        'chapters': []
    }

    # Process each document in the EPUB
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Parse the HTML content
            soup = BeautifulSoup(item.get_content(), 'html.parser')

            # Extract title (try different methods)
            title = ""
            if soup.title:
                title = soup.title.string
            elif soup.find('h1'):
                title = soup.find('h1').get_text()

            # Clean up the text
            text = soup.get_text()
            text = ' '.join(text.split())  # Remove excessive whitespace

            # Add to results
            chapter_data = {
                'file_name': item.get_name(),
                'title': title.strip(),
                'content': text
            }
            result['chapters'].append(chapter_data)

            # If output folder specified, save to file
            if output_folder:
                os.makedirs(output_folder, exist_ok=True)
                base_name = os.path.splitext(os.path.basename(item.get_name()))[0]
                output_path = os.path.join(output_folder, f"{base_name}.txt")

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {title}\n\n")
                    f.write(text)

    if not output_folder:
        return result


# async def extract_text_from_pdf(file) -> str:
#     """Improved PDF text extraction with layout preservation"""
#     pdf_content = await file.read()
#     full_text = ""
#
#     with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
#         for page in pdf.pages:
#             # Extract text with careful layout handling
#             text = page.extract_text(
#                 layout=True,
#                 x_tolerance=2,
#                 y_tolerance=2,
#                 keep_blank_chars=False,
#                 use_text_flow=True
#             ) or ""
#
#             # Clean and add page separator
#             text = clean_text(text)
#             if text:
#                 full_text += f"\nPAGE {page.page_number}\n{text}\n"
#
#     return full_text
#



