import requests
from urllib.parse import quote
import base64
import time
import os # For path operations

from config import GITHUB_API_BASE_URL, MAX_FILE_SIZE_FOR_CONTEXT_BYTES, MAX_CONSOLIDATED_TEXT_LENGTH_CHARS
from utils import format_github_api_error

# --- GitHub API Helper Functions ---

def get_github_api_headers(token: str):
    """Returns headers for GitHub API requests."""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28" # Good practice to specify version
    }

def fetch_user_repos(token: str):
    """Fetches all repositories for the authenticated user."""
    repos = []
    headers = get_github_api_headers(token)
    # Get all repos user has access to, sorted by last push, 100 per page
    url = f"{GITHUB_API_BASE_URL}/user/repos?type=all&sort=pushed&direction=desc&per_page=30" # Max 100, but 30 is fine for testing
    
    page = 1
    while url:
        print(f"Fetching GitHub repos page {page} from {url}...")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            current_page_repos = response.json()
            if not current_page_repos:
                break
            repos.extend(current_page_repos)
            
            # Limit pages fetched for prototype to avoid excessive API calls if user has many repos
            if page >= 2: # Fetch up to 2 pages (e.g. 60 repos if per_page=30)
                print("Reached prototype page limit for fetching repositories.")
                break

            if 'next' in response.links:
                url = response.links['next']['url']
                page += 1
            else:
                url = None
        except requests.exceptions.HTTPError as e:
            return {"error": format_github_api_error(e), "data": []}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e}", "data": []}
        time.sleep(0.3) # Small delay to be nice to GitHub API
            
    return {"error": None, "data": repos}


def fetch_repo_contents_list(token: str, owner: str, repo_name: str, path: str = ""):
    """Fetches the list of contents (files/directories) for a given path in a repository."""
    headers = get_github_api_headers(token)
    encoded_path = quote(path)
    url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo_name}/contents/{encoded_path}"
    print(f"Fetching content list for {owner}/{repo_name} at path '{path}' from {url}")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        contents = response.json()
        # If the path points directly to a file, the API returns a single object, not a list.
        # For directory listing, we expect a list.
        if not isinstance(contents, list):
            # This case might occur if 'path' directly names a file.
            # For a directory browser, this is unexpected. We could return it as a single-item list if needed.
            print(f"Warning: Path '{path}' in {owner}/{repo_name} did not return a list. It might be a file. Returning as empty for dir listing.")
            return {"error": None, "data": []} # Or handle as a single file if API allows that for /contents
        
        # Sort: directories first, then files, all alphabetically
        contents.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))
        return {"error": None, "data": contents}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404 and "This repository is empty." in e.response.text:
            print(f"Repository {owner}/{repo_name} at path '{path}' is empty or path not found (404).")
            return {"error": None, "data": []} # Treat as empty directory
        return {"error": format_github_api_error(e), "data": []}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {e}", "data": []}


def fetch_raw_file_content_from_url(token: str, download_url: str):
    """Fetches raw content of a file given its download_url."""
    if not download_url:
        return {"error": "No download URL provided.", "data": None, "is_binary": False}
    
    headers = get_github_api_headers(token)
    # For raw content, sometimes GitHub prefers no specific "Accept" or a generic one.
    # The default from get_github_api_headers should usually be fine.

    print(f"Fetching raw file content from: {download_url[:100]}...") # Log truncated URL
    try:
        response = requests.get(download_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Try to decode as UTF-8, fall back if it fails (binary content)
        try:
            decoded_content = response.content.decode('utf-8')
            return {"error": None, "data": decoded_content, "is_binary": False}
        except UnicodeDecodeError:
            print(f"File at {download_url[:50]}... appears to be binary or not UTF-8.")
            # For CV context, we mostly care about text. If it's binary, we might skip it.
            return {"error": "File is binary or not UTF-8 decodable.", "data": None, "is_binary": True}
    except requests.exceptions.HTTPError as e:
        return {"error": format_github_api_error(e), "data": None, "is_binary": False}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed for {download_url[:50]}...: {e}", "data": None, "is_binary": False}


def get_consolidated_repo_text_for_context(token: str, owner: str, repo_name: str, max_files_to_check=20):
    """
    Fetches content from prioritized files in the repo root and a few other strategic locations,
    consolidates them into a single string, respecting MAX_CONSOLIDATED_TEXT_LENGTH_CHARS.
    """
    print(f"Consolidating text for context in {owner}/{repo_name}")
    consolidated_text = ""
    current_length = 0
    files_processed_count = 0

    # Path Traversal Logic: Explore root, then common dirs like 'src', 'lib'
    # This is a simplified traversal. A full recursive traversal could be too slow/complex for this prototype.
    paths_to_check = [""] # Start with root
    
    # Basic check for common source directories - could be expanded
    # We do a quick list of root to see if 'src' or 'lib' exist without deep scan
    root_contents_result = fetch_repo_contents_list(token, owner, repo_name, path="")
    if not root_contents_result["error"] and root_contents_result["data"]:
        for item in root_contents_result["data"]:
            if item.get("type") == "dir" and item.get("name", "").lower() in ["src", "lib", "app", "source"]:
                paths_to_check.append(item.get("name"))

    # Priority: README files first from any checked path
    readme_found_and_added = False
    for path_prefix in paths_to_check:
        if readme_found_and_added or current_length >= MAX_CONSOLIDATED_TEXT_LENGTH_CHARS:
            break
        contents_result = fetch_repo_contents_list(token, owner, repo_name, path=path_prefix)
        if not contents_result["error"] and contents_result["data"]:
            for item in contents_result["data"]:
                if files_processed_count >= max_files_to_check or current_length >= MAX_CONSOLIDATED_TEXT_LENGTH_CHARS:
                    break
                if item.get("type") == "file" and item.get("name", "").lower().startswith("readme"):
                    if item.get("size", 0) <= MAX_FILE_SIZE_FOR_CONTEXT_BYTES and item.get("download_url"):
                        content_result = fetch_raw_file_content_from_url(token, item.get("download_url"))
                        if not content_result["error"] and not content_result["is_binary"] and content_result["data"]:
                            text_to_add = f"\n\n--- Content from: {item['path']} ---\n{content_result['data']}"
                            if current_length + len(text_to_add) <= MAX_CONSOLIDATED_TEXT_LENGTH_CHARS:
                                consolidated_text += text_to_add
                                current_length += len(text_to_add)
                                files_processed_count += 1
                                readme_found_and_added = True # Prioritize one good README
                                print(f"Added {item['path']} to context.")
                                break # Stop looking for READMEs if one good one is found
            if readme_found_and_added: break


    # Then, other common text files
    common_extensions = ('.py', '.js', '.ts', '.java', '.go', '.rb', '.php', '.md', '.txt', 
                         '.json', '.yaml', '.yml', '.xml', '.html', '.css', '.sh', '.R', '.scala', '.kt', '.swift', '.c', '.cpp', '.h', '.cs')

    for path_prefix in paths_to_check: # Iterate through root, then 'src', etc.
        if current_length >= MAX_CONSOLIDATED_TEXT_LENGTH_CHARS or files_processed_count >= max_files_to_check:
            break
        
        contents_result = fetch_repo_contents_list(token, owner, repo_name, path=path_prefix)
        if contents_result["error"] or not contents_result["data"]:
            continue

        # Sort files by a heuristic (e.g., common names like main, app, index, then by size)
        # This is a simple sort, can be improved.
        sorted_files = sorted(
            [item for item in contents_result["data"] if item.get("type") == "file"],
            key=lambda x: (
                0 if x.get("name", "").lower() in ["main.py", "app.py", "index.js", "server.js"] else 1,
                x.get("size", float('inf')) # Smaller files next if not primary
            )
        )

        for item in sorted_files:
            if current_length >= MAX_CONSOLIDATED_TEXT_LENGTH_CHARS or files_processed_count >= max_files_to_check:
                break
            
            file_name_lower = item.get("name", "").lower()
            if file_name_lower.startswith("readme") and readme_found_and_added: # Skip if we already got a README
                continue

            if file_name_lower.endswith(common_extensions):
                if item.get("size", 0) <= MAX_FILE_SIZE_FOR_CONTEXT_BYTES and item.get("download_url"):
                    content_result = fetch_raw_file_content_from_url(token, item.get("download_url"))
                    if not content_result["error"] and not content_result["is_binary"] and content_result["data"]:
                        text_to_add = f"\n\n--- Content from: {item['path']} ---\n{content_result['data']}"
                        if current_length + len(text_to_add) <= MAX_CONSOLIDATED_TEXT_LENGTH_CHARS:
                            consolidated_text += text_to_add
                            current_length += len(text_to_add)
                            files_processed_count += 1
                            print(f"Added {item['path']} to context.")
                        else:
                            # Try adding a truncated version if it doesn't fit fully
                            remaining_space = MAX_CONSOLIDATED_TEXT_LENGTH_CHARS - current_length
                            if remaining_space > 200: # Only add if a meaningful snippet can fit
                                truncated_content = content_result['data'][:(remaining_space - len(f"\n\n--- Content from: {item['path']} ---\n... (truncated)"))] + "... (truncated)"
                                text_to_add_truncated = f"\n\n--- Content from: {item['path']} ---\n{truncated_content}"
                                consolidated_text += text_to_add_truncated
                                current_length += len(text_to_add_truncated)
                                files_processed_count += 1
                                print(f"Added truncated {item['path']} to context.")
                            break # Stop adding more files if we hit the consolidated limit
    
    if not consolidated_text.strip():
        print(f"No suitable text files found or fetched for context consolidation in {owner}/{repo_name}.")
        return None

    print(f"Consolidated text length for {owner}/{repo_name}: {len(consolidated_text)} chars from {files_processed_count} file portions.")
    return consolidated_text.strip()
