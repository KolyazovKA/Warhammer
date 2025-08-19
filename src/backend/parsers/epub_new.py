import io
import os

import ebooklib
from bs4 import BeautifulSoup
from ebooklib import epub


# extract_epub_text_with_metadata
def extract_text_from_epub(file_content: bytes, output_folder=None):
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