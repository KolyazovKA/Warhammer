import xml.etree.ElementTree as ET

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