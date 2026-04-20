import defusedxml.ElementTree as ET


def extract_text_from_fb2(file_content: bytes) -> str:
    """Extract text from FB2 (FictionBook) format."""
    try:
        root = ET.fromstring(file_content)
        ns = {'fb2': 'http://www.gribuser.ru/xml/fictionbook/2.0'}

        bodies = root.findall('.//fb2:body', ns) or root.findall('.//body')
        text_parts = []

        for body in bodies:
            paragraphs = body.findall('.//fb2:p', ns) or body.findall('.//p')
            for p in paragraphs:
                text_parts.append(''.join(p.itertext()))

        return '\n\n'.join(text_parts)
    except ET.ParseError as e:
        raise ValueError(f"Failed to parse FB2 file: {str(e)}")