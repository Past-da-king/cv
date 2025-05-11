import html
import markdown # Import markdown library
import re # Import regex for potential manual list formatting if needed

def format_github_api_error(e):
    """Formats HTTPError from GitHub API requests."""
    error_message = f"GitHub API Error: {e.response.status_code}"
    try:
        error_detail = e.response.json().get("message", e.response.text)
        error_message += f" - {error_detail}"
    except ValueError: 
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
        start += (chunk_size - chunk_overlap)
        if start >= end and chunk_overlap > 0: 
             break
        if start >= text_len and chunk_overlap > 0: # Handle cases where last chunk is smaller than overlap
             break 

    return [chunk for chunk in chunks if chunk.strip()]


def escape_html_chars(text_content):
    """Escapes HTML special characters in text content."""
    if not text_content:
        return ""
    # Ensure input is string before escaping
    return html.escape(str(text_content)) 

def markdown_to_html(markdown_text):
    """Converts Markdown text to HTML."""
    if not markdown_text:
        return ""
    try:
        # Use the markdown library to convert with common extensions
        # 'nl2br': Converts newlines within paragraphs to <br>
        # 'fenced_code': For ```code blocks```
        # 'extra': Includes several extensions like tables, footnotes, etc.
        # 'attr_list': Allows adding {:#id .class} to elements - useful with Tailwind prose
        html_output = markdown.markdown(markdown_text, extensions=['nl2br', 'fenced_code', 'extra', 'attr_list'], output_format='html5')
        
        # --- Optional: Post-process HTML if specific styles are needed beyond prose ---
        # Example: Add a specific class to strong tags that look like section titles
        # This requires a more complex regex and might be fragile if AI output varies
        # html_output = re.sub(r'<p><strong>(Project Title|Project Overview|Key Technical Features &amp; Accomplishments|Technologies Used):<\/strong><\/p>', 
        #                      r'<p><strong class="section-title">\1:</strong></p>', html_output) # Example regex
        # Note: need to escape the & for &amp; if markdown converts it.

        # Example: Add a class to list items for custom styling
        # This is harder to do reliably with just regex on the generated HTML.
        # Relying on the typography plugin is generally better.

        return html_output
    except Exception as e:
        print(f"Error converting markdown to HTML: {e}")
        # Fallback to just escaping in case of error
        return escape_html_chars(markdown_text)

