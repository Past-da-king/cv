import html

def format_github_api_error(e):
    """Formats HTTPError from GitHub API requests."""
    error_message = f"GitHub API Error: {e.response.status_code}"
    try:
        error_detail = e.response.json().get("message", e.response.text)
        error_message += f" - {error_detail}"
    except ValueError: # If response is not JSON
        error_message += f" - {e.response.text}"
    return error_message

def simple_chunk_text(text, chunk_size, chunk_overlap):
    """Simple text chunker based on character count with overlap."""
    if not text or not text.strip():
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end == text_len:
            break
        # Move start forward, ensuring it doesn't create tiny overlaps leading to issues
        start += (chunk_size - chunk_overlap)
        # Safety break if chunking logic is flawed for very small texts + large overlaps
        if start >= end : break 
    return [chunk for chunk in chunks if chunk.strip()]


def escape_html_chars(text_content):
    """Escapes HTML special characters in text content."""
    if not text_content:
        return ""
    return html.escape(str(text_content)) # Ensure it's a string
