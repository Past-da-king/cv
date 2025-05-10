import uvicorn
from fastapi import FastAPI, Request, Form, Query, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates 
from typing import Optional, List
import os
from urllib.parse import quote, unquote
import re 
import html as html_escaper 

import config 
from config import (
    APP_TITLE, APP_VERSION, GOOGLE_API_KEY,
    MAX_REPOS_TO_DISPLAY_FOR_SELECTION,
    AUTO_SELECT_PROCESS_COUNT, AUTO_SELECT_FINAL_OUTPUT_COUNT,
    MAX_MANUAL_SELECT_REPOS_FOR_CV,
    USE_LOCAL_EMBEDDINGS 
)
from github_service import (
    fetch_user_repos, fetch_repo_contents_list,
    fetch_raw_file_content_from_url
)
from cv_generator_logic import orchestrate_cv_generation_for_repos
from utils import escape_html_chars
from vector_store_service import load_vector_store 
from local_embedding_service import local_embedder_model 

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# Ensure the templates directory is correctly referenced relative to main.py
# If templates is in 'cv/templates' and main.py is in 'cv/', then "templates" is correct.
templates = Jinja2Templates(directory="templates") 
app.state.user_repos_cache = None 

if os.path.exists("static"):
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    # Attempt to mount from 'cv/static' if main.py is in the root above 'cv'
    static_dir_alt = os.path.join(os.path.dirname(__file__), "static")
    if os.path.exists(static_dir_alt):
         app.mount("/static", StaticFiles(directory=static_dir_alt), name="static")
    else:
        print("Warning: Static directory not found at 'static/' or 'cv/static/'. Ensure it's correctly placed.")


@app.on_event("startup")
async def startup_event():
    print(f"Starting {APP_TITLE} v{APP_VERSION}...")
    if not GOOGLE_API_KEY:
        print("CRITICAL WARNING: GOOGLE_API_KEY not set. CV Generation (Gemini) will NOT work.")
    else:
        print("GOOGLE_API_KEY found.")
    if local_embedder_model is None and USE_LOCAL_EMBEDDINGS: 
         print("CRITICAL WARNING: Local embedding model failed to load. CV context building will not work correctly.")
    elif USE_LOCAL_EMBEDDINGS: 
        print(f"Using local embeddings with model: {config.LOCAL_EMBEDDING_MODEL_NAME}")
    else:
        print(f"Using Gemini API for embeddings with model: {config.GEMINI_EMBEDDING_MODEL_NAME} (Rate limits apply!)")
    
    print("Attempting to load vector store from disk...")
    load_vector_store() 

@app.get("/", response_class=HTMLResponse)
async def get_token_form_page(request: Request, error: Optional[str] = None):
    # Check if already authenticated, redirect to repos if so
    if request.cookies.get("github_pat"):
        # Before redirecting, try fetching repos to see if token is still valid
        # This is a bit heavy for just a check, could be a lighter ping to GitHub API
        # For now, this check is removed for simplicity, relying on user to re-auth if token invalid.
        # User will hit an error on /repos if token is bad.
        pass # Pass, means token_form will be shown. Can be adjusted.
             # Consider a redirect to /repos if request.cookies.get("github_pat")
             # but handle token expiry gracefully.

    return templates.TemplateResponse("token_form.html", {
        "request": request, 
        "error_message": unquote(error) if error else None,
        "app_title": APP_TITLE,
        "app_version": APP_VERSION,
    })

@app.post("/auth/set-token")
async def set_github_token(request: Request, token: str = Form(...)):
    if not token or not token.strip():
        error_msg = quote("GitHub PAT cannot be empty.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)
    
    response = RedirectResponse(url="/repos", status_code=303)
    response.set_cookie(
        key="github_pat", value=token, httponly=True, 
        samesite="lax", max_age=3600 * 24 * 7, # Cookie for 7 days
        secure=request.url.scheme == "https", path="/"
    ) 
    return response

@app.get("/repos", response_class=HTMLResponse)
async def list_repositories_page(request: Request, github_pat: Optional[str] = Cookie(None)):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired. Please enter it again to connect.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    result = fetch_user_repos(github_pat) 
    
    repo_cards_html = ""
    error_message_for_template = None

    if result["error"]:
        error_message_for_template = f'{escape_html_chars(result["error"])} You might need to re-enter your token.'
    elif not result["data"]:
        repo_cards_html = "" # No specific message here, template will handle "No Repositories Found"
    else:
        card_items = []
        repos_to_display = result["data"][:MAX_REPOS_TO_DISPLAY_FOR_SELECTION]
        app.state.user_repos_cache = result["data"] 

        for repo in repos_to_display:
            repo_full_name = repo.get("full_name", "N/A")
            repo_full_name_escaped = escape_html_chars(repo_full_name)
            owner_login = escape_html_chars(repo.get("owner", {}).get("login", ""))
            repo_name_only = escape_html_chars(repo.get("name", ""))
            
            language = repo.get("language")
            language_escaped = escape_html_chars(language if language else "N/A")
            
            pushed_at_raw = repo.get("pushed_at", "N/A")
            pushed_at_date = pushed_at_raw[:10] if pushed_at_raw != "N/A" else "N/A"
            pushed_at_escaped = escape_html_chars(pushed_at_date)

            visibility = repo.get("visibility", "N/A")
            visibility_escaped = escape_html_chars(visibility.capitalize())
            
            description_raw = repo.get("description") 
            if description_raw and isinstance(description_raw, str): 
                description_truncated = description_raw[:120] # Slightly more
                if len(description_raw) > 120:
                    description_truncated += "..."
                description_escaped = escape_html_chars(description_truncated)
            else:
                description_escaped = "No description provided."
            
            star_count = repo.get("stargazers_count", 0)
            fork_count = repo.get("forks_count", 0)

            card_items.append(f'''
<div class="bg-white rounded-xl shadow-lg border border-slate-200 hover:shadow-xl transition-shadow duration-300 ease-in-out flex flex-col overflow-hidden">
    <div class="p-5 sm:p-6 flex-grow">
        <div class="flex items-start space-x-3 mb-3">
            <input type="checkbox" name="selected_repos" value="{repo_full_name_escaped}" class="h-5 w-5 text-primary-DEFAULT border-slate-300 rounded focus:ring-primary-DEFAULT mt-1 cursor-pointer">
            <div class="flex-1 min-w-0">
                <h3 class="text-lg font-semibold text-slate-800 hover:text-primary-DEFAULT transition-colors leading-tight">
                    <a href="/repo/{owner_login}/{repo_name_only}" class="block truncate" title="Browse {repo_full_name_escaped}">{repo_full_name_escaped}</a>
                </h3>
                <p class="text-xs text-slate-500 mt-0.5">
                    Last pushed: {pushed_at_escaped}
                </p>
            </div>
        </div>
        <p class="text-sm text-slate-600 mb-4 h-16 overflow-hidden leading-relaxed">{description_escaped}</p> 
    </div>
    <div class="px-5 sm:px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
        <span class="inline-flex items-center gap-1.5">
            <span class="capitalize px-2 py-0.5 bg-slate-200 text-slate-700 rounded-full font-medium">{visibility_escaped}</span>
            {(f'<span class="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full font-medium">{language_escaped}</span>') if language else ''}
        </span>
        <span class="flex items-center gap-3">
            <span class="flex items-center" title="{star_count} stars">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-amber-400 mr-0.5"><path fill-rule="evenodd" d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.393c-.83.069-.996 1.033-.464 1.491l3.493 3.01-1.057 4.637c-.19.825.743 1.44 1.482 1.06l4.116-2.512 4.116 2.512c.74.38 1.673-.235 1.482-1.06l-1.057-4.637 3.494-3.01c.531-.458.366-1.422-.464-1.491l-4.753-.393-1.83-4.401z" clip-rule="evenodd" /></svg>
                {star_count}
            </span>
            <span class="flex items-center" title="{fork_count} forks">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-slate-400 mr-0.5"><path fill-rule="evenodd" d="M10 2c-2.236 0-4.048.032-5.454.144C3.044 2.264 2 3.22 2 4.544v8.912c0 1.324 1.043 2.28 2.546 2.402C6.03 16.005 8.005 16 10 16s3.97-.005 5.454-.144c1.503-.122 2.546-1.078 2.546-2.402V4.544c0-1.324-1.043-2.28-2.546-2.402C13.969 2.032 12.236 2 10 2zM6.67 10.43a2.5 2.5 0 100-5 2.5 2.5 0 000 5zm6.66 0a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" clip-rule="evenodd" /></svg>
                {fork_count}
            </span>
        </span>
    </div>
</div>
            ''')
        repo_cards_html = "".join(card_items)
        
    return templates.TemplateResponse("repo_list.html", {
        "request": request,
        "error_message": error_message_for_template,
        "repo_cards_html": repo_cards_html,
        "max_manual_select_repos": MAX_MANUAL_SELECT_REPOS_FOR_CV,
        "auto_select_process_count": AUTO_SELECT_PROCESS_COUNT,
        "auto_select_output_count": AUTO_SELECT_FINAL_OUTPUT_COUNT,
        "app_title": APP_TITLE,
        "app_version": APP_VERSION,
    })

@app.get("/repo/{owner}/{repo_name}", response_class=HTMLResponse)
async def view_repo_directory_contents(
    request: Request, owner: str, repo_name: str,
    path: str = Query(""), github_pat: Optional[str] = Cookie(None)
):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired. Please connect again.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    current_path_unquoted = unquote(path)
    result = fetch_repo_contents_list(github_pat, owner, repo_name, current_path_unquoted)
    
    content_list_html_items = "" 
    error_message_for_template = None

    if result["error"]:
        error_message_for_template = escape_html_chars(result["error"])
    elif not result["data"] and not current_path_unquoted: # Empty repo root
         pass # Template will show "Directory Empty"
    elif not result["data"] and current_path_unquoted: # Empty subdirectory
         pass # Template will show "Directory Empty"
    else:
        items = []
        for item in result["data"]:
            item_name_escaped = escape_html_chars(item.get("name", "N/A"))
            item_path_raw = item.get("path", "")
            encoded_item_path = quote(item_path_raw)
            item_type = item.get("type", "unknown")

            icon_svg = ""
            link_class = "font-medium text-slate-700 hover:text-primary-DEFAULT transition-colors group-hover:text-primary-DEFAULT"
            item_details = ""
            action_text = "Open"

            if item_type == "dir":
                icon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-amber-500 group-hover:text-amber-600 transition-colors"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" /></svg>'''
                link_target = f'/repo/{owner}/{repo_name}?path={encoded_item_path}'
                item_details = f"<span class='text-xs text-slate-400'>Directory</span>"
                action_text = "Browse"
            elif item_type == "file":
                icon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-slate-400 group-hover:text-slate-500 transition-colors"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V8a2 2 0 00-2-2h-5L9 4H4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z" clip-rule="evenodd" /></svg>'''
                link_target = f'/repo/{owner}/{repo_name}/file?path={encoded_item_path}'
                item_size_bytes = item.get('size', 0)
                item_details = f"<span class='text-xs text-slate-400'>{item_size_bytes} bytes</span>"
                action_text = "View File"
            else: # Symlink or other
                icon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-slate-400"><path fill-rule="evenodd" d="M12.207 2.207a1 1 0 011.414 0l4.25 4.25a1 1 0 010 1.414l-4.25 4.25a1 1 0 01-1.414-1.414L14.586 9H4.75a1 1 0 110-2h9.836L12.207 3.621a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>'''
                link_target = "#" 
                link_class = "text-slate-500 cursor-default"
                item_details = f"<span class='text-xs text-slate-400'>(type: {escape_html_chars(item_type)})</span>"
                action_text = "N/A"
            
            items.append(f'''
            <li class="group">
                <a href="{link_target}" class="block hover:bg-slate-50 transition-colors">
                    <div class="flex items-center justify-between px-4 py-4 sm:px-6">
                        <div class="flex items-center min-w-0 space-x-3">
                            {icon_svg}
                            <p class="truncate text-sm {link_class}">{item_name_escaped}</p>
                        </div>
                        <div class="flex items-center space-x-3 ml-2">
                            {item_details}
                            <svg class="h-5 w-5 text-slate-400 group-hover:text-slate-500 transition-colors" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
                            </svg>
                        </div>
                    </div>
                </a>
            </li>
            ''')
        content_list_html_items = "".join(items)
    
    up_link_html = ""
    if current_path_unquoted:
        parent_path = os.path.dirname(current_path_unquoted)
        encoded_parent_path = quote(parent_path)
        # This will be used in the template's header/breadcrumb area now
        up_link_html = f'''
        <a href="/repo/{owner}/{repo_name}?path={encoded_parent_path}" 
           class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50 transition-colors">
            <svg class="-ml-0.5 mr-1.5 h-5 w-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                <path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd"></path>
            </svg>
            Up one level
        </a>'''
    
    return templates.TemplateResponse("repo_contents.html", {
        "request": request,
        "repo_full_name": escape_html_chars(f"{owner}/{repo_name}"),
        "current_path_display": escape_html_chars(current_path_unquoted if current_path_unquoted else "(root)"),
        "up_link": up_link_html, 
        "content_list_html_items": content_list_html_items,
        "error_message": error_message_for_template,
        "app_title": APP_TITLE,
        "app_version": APP_VERSION,
    })


@app.post("/generate-cv-summary", response_class=HTMLResponse)
async def generate_cv_summary_page(
    request: Request, 
    github_pat: Optional[str] = Cookie(None),
    action_type: str = Form(...), 
    selected_repo_names: Optional[List[str]] = Form(None) 
):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired. Cannot generate CV summary.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    if not GOOGLE_API_KEY: 
        message = "Google API Key not configured. CV generation feature is disabled."
        return templates.TemplateResponse("cv_summary.html", {
            "request": request, "message": message, "cv_entries_html_parts": [], 
            "app_title": APP_TITLE, "app_version": APP_VERSION,
        })

    all_fetched_repos = getattr(app.state, 'user_repos_cache', None)
    if not all_fetched_repos:
        fetch_result = fetch_user_repos(github_pat)
        if fetch_result["error"] or not fetch_result["data"]:
            message = f'Could not fetch repositories for CV generation: {escape_html_chars(fetch_result.get("error", "No data"))}'
            return templates.TemplateResponse("cv_summary.html", {
                "request": request, "message": message, "cv_entries_html_parts": [], 
                "app_title": APP_TITLE, "app_version": APP_VERSION,
            })
        all_fetched_repos = fetch_result["data"]
        app.state.user_repos_cache = all_fetched_repos

    repos_to_actually_process = []
    if action_type == 'manual_select':
        if not selected_repo_names: 
            message = "No repositories were selected for manual processing."
            return templates.TemplateResponse("cv_summary.html", {
                "request": request, "message": message, "cv_entries_html_parts": [],
                "app_title": APP_TITLE, "app_version": APP_VERSION,
            })
        
        selected_repo_names_set = set(selected_repo_names)
        repos_to_actually_process = [repo for repo in all_fetched_repos if repo.get("full_name") in selected_repo_names_set]
        
        if len(repos_to_actually_process) > MAX_MANUAL_SELECT_REPOS_FOR_CV:
            message = f"Too many repositories selected. Please select no more than {MAX_MANUAL_SELECT_REPOS_FOR_CV}."
            return templates.TemplateResponse("cv_summary.html", {
                "request": request, "message": message, "cv_entries_html_parts": [],
                "app_title": APP_TITLE, "app_version": APP_VERSION,
            })

    elif action_type == 'auto_select':
        repos_to_actually_process = all_fetched_repos[:AUTO_SELECT_PROCESS_COUNT]
    else:
        message = "Invalid action type for CV generation."
        return templates.TemplateResponse("cv_summary.html", {
            "request": request, "message": message, "cv_entries_html_parts": [],
            "app_title": APP_TITLE, "app_version": APP_VERSION,
        })

    if not repos_to_actually_process:
        message = 'No repositories selected or available for CV summary processing.'
        return templates.TemplateResponse("cv_summary.html", {
            "request": request, "message": message, "cv_entries_html_parts": [],
            "app_title": APP_TITLE, "app_version": APP_VERSION,
        })

    print(f"Starting CV generation. Action: '{action_type}'. Repos to process: {[r.get('full_name') for r in repos_to_actually_process]}")
    generated_cvs_data = orchestrate_cv_generation_for_repos(github_pat, repos_to_actually_process, action_type)
    print("Finished CV generation orchestration.")

    cv_entries_html_result_parts = [] 
    successful_cv_count = 0
    
    for cv_data in generated_cvs_data: 
        repo_name_esc = escape_html_chars(cv_data.get("repo", "Unknown Repo"))
        if cv_data.get("cv_entry"):
            successful_cv_count +=1
            cv_text_raw = cv_data["cv_entry"]
            # Apply HTML escaping first, then nl2br, then regex for bolding and lists
            cv_text_html = escape_html_chars(cv_text_raw).replace("\n", "<br />\n")
            cv_text_html = re.sub(r'\*\*(Project Description|Key Features/Accomplishments|Technologies Used|Key Highlights|Project Overview):\*\*', r'<strong class="block mt-3 mb-1.5 text-slate-800 font-semibold text-base">\1:</strong>', cv_text_html)
            # Improved list item handling:
            # This regex tries to match list items more robustly after <br /> tags.
            # It wraps the content after the bullet in a span for better styling control if needed.
            cv_text_html = re.sub(r'(?:<br />\s*)+([\*\-•]\s+)(.+)', r'<br /><span class="list-bullet">• </span><span class="list-item-content">\2</span>', cv_text_html, flags=re.MULTILINE)
            # If the above is too complex or has issues, revert to simpler one:
            # cv_text_html = re.sub(r'(<br />\s*[\*\-•]\s+)', r'<br /><span class="ml-4 inline-block text-slate-600">•&nbsp;</span>', cv_text_html, flags=re.MULTILINE)


            cv_entries_html_result_parts.append(f"""
            <article class="bg-white p-6 sm:p-8 rounded-xl shadow-xl border border-slate-200">
                <h3 class="text-xl font-semibold text-primary-DEFAULT mb-4">{repo_name_esc}</h3>
                <div class="prose prose-slate max-w-none cv-content-body">
                    {cv_text_html}
                </div>
            </article>
            """)
        elif cv_data.get("error"):
            cv_entries_html_result_parts.append(f"""
            <article class="bg-red-50 p-6 sm:p-8 rounded-xl shadow-lg border border-red-200 text-red-700">
                <div class="flex items-start space-x-3">
                    <svg class="flex-shrink-0 w-6 h-6 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286zm0 13.036h.008v.008H12v-.008z" />
                    </svg>
                    <div>
                        <h3 class="text-xl font-semibold mb-2">{repo_name_esc}</h3>
                        <p class="text-sm"><strong class="font-medium">CV Generation Failed:</strong> {escape_html_chars(cv_data["error"])}</p>
                    </div>
                </div>
            </article>
            """)
    
    actual_processed_count = len(repos_to_actually_process)
    final_message_text = f"Attempted processing for {actual_processed_count} repositories. "
    
    if action_type == 'auto_select':
        final_message_text += f"Selected top {successful_cv_count} of {AUTO_SELECT_FINAL_OUTPUT_COUNT} targeted successful CV entries from {AUTO_SELECT_PROCESS_COUNT} processed. "
    else: # manual_select
        final_message_text += f"Generated {successful_cv_count} CV entries. "

    errors_occurred_in_displayed_results = any(cv_data.get("error") for cv_data in generated_cvs_data if not cv_data.get("cv_entry"))
    not_all_targeted_successful = (action_type == 'auto_select' and successful_cv_count < AUTO_SELECT_FINAL_OUTPUT_COUNT) or \
                                  (action_type == 'manual_select' and successful_cv_count < len(repos_to_actually_process))


    if errors_occurred_in_displayed_results or not_all_targeted_successful:
         final_message_text += " Some summaries may not have been generated due to errors or selection criteria. Check entries below or server logs."
        
    return templates.TemplateResponse("cv_summary.html", {
        "request": request,
        "message": final_message_text,
        "cv_entries_html_parts": cv_entries_html_result_parts,
        "app_title": APP_TITLE,
        "app_version": APP_VERSION,
    })

# --- Main Execution ---
if __name__ == "__main__":
    # This check allows running with `python main.py` or `python cv/main.py`
    # It assumes uvicorn is in PATH or accessible.
    is_direct_run = __file__.endswith("main.py") 
    app_module_path = "main:app" if is_direct_run else "cv.main:app"
    
    # Ensure current working directory is the project root for uvicorn reload
    project_root = os.path.dirname(os.path.abspath(__file__))
    if not is_direct_run: # if running cv/main.py, root is one level up
        project_root = os.path.dirname(project_root)
    
    print(f"Running uvicorn for module: {app_module_path} from CWD: {project_root}")

    try:
        # Change CWD for uvicorn if necessary, especially for reload
        os.chdir(project_root) 
        uvicorn.run(app_module_path, host="127.0.0.1", port=8000, reload=True, reload_dirs=[os.path.join(project_root, "cv")])
    except ImportError as e:
        print(f"ImportError: {e}. Could not run uvicorn. Is it installed and in PATH?")
        print("Try: pip install uvicorn[standard]")
        print(f"To run manually: uvicorn {app_module_path} --reload --host 127.0.0.1 --port 8000 --reload-dir cv")
    except Exception as e:
        print(f"An error occurred: {e}")

