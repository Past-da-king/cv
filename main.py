import uvicorn
from fastapi import FastAPI, Request, Form, Query, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates # For serving HTML files
from typing import Optional, List
import os
from urllib.parse import quote, unquote
import re 
import html as html_escaper 

import config # Import the whole module to access all its variables
from config import (
    APP_TITLE, APP_VERSION, GOOGLE_API_KEY,
    MAX_REPOS_TO_DISPLAY_FOR_SELECTION,
    AUTO_SELECT_PROCESS_COUNT, AUTO_SELECT_FINAL_OUTPUT_COUNT,
    MAX_MANUAL_SELECT_REPOS_FOR_CV,
    USE_LOCAL_EMBEDDINGS # For startup message
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
templates = Jinja2Templates(directory="templates")
app.state.user_repos_cache = None 

if os.path.exists("static"):
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    print(f"Starting {APP_TITLE} v{APP_VERSION}...")
    if not GOOGLE_API_KEY:
        print("CRITICAL WARNING: GOOGLE_API_KEY not set. CV Generation (Gemini) will NOT work.")
    else:
        print("GOOGLE_API_KEY found.")
    if local_embedder_model is None and USE_LOCAL_EMBEDDINGS: # Use USE_LOCAL_EMBEDDINGS from config
         print("CRITICAL WARNING: Local embedding model failed to load. CV context building will not work correctly.")
    elif USE_LOCAL_EMBEDDINGS: # Use USE_LOCAL_EMBEDDINGS from config
        print(f"Using local embeddings with model: {config.LOCAL_EMBEDDING_MODEL_NAME}")
    else:
        print(f"Using Gemini API for embeddings with model: {config.GEMINI_EMBEDDING_MODEL_NAME} (Rate limits apply!)")
    # load_vector_store() 

@app.get("/", response_class=HTMLResponse)
async def get_token_form_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("token_form.html", {
        "request": request, 
        "error_message": unquote(error) if error else None,
        "app_title": APP_TITLE
    })

@app.post("/auth/set-token")
async def set_github_token(request: Request, token: str = Form(...)):
    if not token or not token.strip():
        error_msg = quote("GitHub PAT cannot be empty.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)
    
    response = RedirectResponse(url="/repos", status_code=303)
    response.set_cookie(
        key="github_pat", value=token, httponly=True, 
        samesite="lax", max_age=3600 * 24, 
        secure=request.url.scheme == "https", path="/"
    ) 
    return response

@app.get("/repos", response_class=HTMLResponse)
async def list_repositories_page(request: Request, github_pat: Optional[str] = Cookie(None)):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired. Please enter again.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    result = fetch_user_repos(github_pat) 
    
    repo_cards_html = ""
    error_message_for_template = None

    if result["error"]:
        error_message_for_template = f'Could not fetch repositories: {escape_html_chars(result["error"])}'
    elif not result["data"]:
        error_message_for_template = None
        repo_cards_html = "<p class='text-slate-500 py-8 text-center col-span-full'>No repositories found or you don't have access to any.</p>"
    else:
        error_message_for_template = None
        card_items = []
        repos_to_display = result["data"][:MAX_REPOS_TO_DISPLAY_FOR_SELECTION]
        app.state.user_repos_cache = result["data"] 

        for repo in repos_to_display:
            repo_full_name_escaped = escape_html_chars(repo.get("full_name", "N/A"))
            language_escaped = escape_html_chars(repo.get("language", "N/A") if repo.get("language") else "N/A")
            pushed_at_escaped = escape_html_chars(repo.get("pushed_at", "N/A")[:10])
            visibility_escaped = escape_html_chars(repo.get("visibility", "N/A"))
            
            # --- FIX IS HERE ---
            description_raw = repo.get("description") 
            if description_raw and isinstance(description_raw, str): # Check if it's a string
                description_truncated = description_raw[:100]
                if len(description_raw) > 100:
                    description_truncated += "..."
                description_escaped = escape_html_chars(description_truncated)
            else:
                description_escaped = "No description available."
            # --- END OF FIX ---

            card_items.append(f'''
                <div class="bg-white border border-slate-200 rounded-lg shadow-md p-5 hover:shadow-lg transition-shadow duration-200 flex flex-col justify-between">
                    <div>
                        <div class="flex items-center mb-2">
                            <input type="checkbox" name="selected_repos" value="{repo_full_name_escaped}" class="h-5 w-5 text-brand-indigo border-slate-300 rounded focus:ring-brand-indigo mr-3">
                            <h3 class="text-md font-semibold text-brand-blue hover:underline">
                                <a href="/repo/{escape_html_chars(repo.get("owner", {}).get("login", ""))}/{escape_html_chars(repo.get("name", ""))}">{repo_full_name_escaped}</a>
                            </h3>
                        </div>
                        <p class="text-xs text-slate-500 mb-1">
                            <span class="capitalize px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs mr-1">{visibility_escaped}</span>
                            Last pushed: {pushed_at_escaped}
                        </p>
                        <p class="text-sm text-slate-600 mb-3 h-10 overflow-hidden">{description_escaped}</p> 
                    </div>
                    <div class="mt-auto pt-2 border-t border-slate-100">
                        <span class="inline-flex items-center bg-indigo-100 text-brand-indigo text-xs font-medium px-2.5 py-1 rounded-full">
                            {language_escaped}
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
        "app_title": APP_TITLE
    })

@app.get("/repo/{owner}/{repo_name}", response_class=HTMLResponse)
async def view_repo_directory_contents(
    request: Request, owner: str, repo_name: str,
    path: str = Query(""), github_pat: Optional[str] = Cookie(None)
):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    current_path_unquoted = unquote(path)
    result = fetch_repo_contents_list(github_pat, owner, repo_name, current_path_unquoted)
    
    content_list_html_items = "" 
    error_message_for_template = None

    if result["error"]:
        error_message_for_template = escape_html_chars(result["error"])
    elif not result["data"]:
        pass 
    else:
        items = []
        for item in result["data"]:
            item_name_escaped = escape_html_chars(item.get("name", "N/A"))
            item_path_raw = item.get("path", "")
            encoded_item_path = quote(item_path_raw)
            item_type = item.get("type", "unknown")

            icon_svg = ""
            link_class = "text-brand-blue hover:text-brand-indigo font-medium"
            item_details = ""

            if item_type == "dir":
                icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-brand-yellow mr-3 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" /></svg>'
                link_target = f'/repo/{owner}/{repo_name}?path={encoded_item_path}'
            elif item_type == "file":
                icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-slate-500 mr-3 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V8a2 2 0 00-2-2h-5L9 4H4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z" clip-rule="evenodd" /></svg>'
                link_target = f'/repo/{owner}/{repo_name}/file?path={encoded_item_path}'
                item_details = f"<span class='text-xs text-slate-400 ml-auto'>{item.get('size', 0)} B</span>"
            else: 
                icon_svg = '<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-slate-400 mr-3 flex-shrink-0" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M12.293 5.293a1 1 0 011.414 0l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-2.293-2.293a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>'
                link_target = "#" 
                link_class = "text-slate-600 cursor-default"
                item_details = f"<span class='text-xs text-slate-400 ml-auto'>(type: {escape_html_chars(item_type)})</span>"
            
            items.append(f'''
            <li class="flex items-center justify-between py-3.5 px-4 hover:bg-slate-50 transition-colors">
                <div class="flex items-center min-w-0">
                    {icon_svg}
                    <a href="{link_target}" class="{link_class} truncate text-sm">
                        {item_name_escaped}
                    </a>
                </div>
                {item_details}
            </li>
            ''')
        content_list_html_items = "".join(items)
    
    up_link_html = ""
    if current_path_unquoted:
        parent_path = os.path.dirname(current_path_unquoted)
        encoded_parent_path = quote(parent_path)
        up_link_html = f'''<a href="/repo/{owner}/{repo_name}?path={encoded_parent_path}" 
                           class="text-brand-blue hover:text-brand-indigo font-medium flex items-center py-1 transition-colors">
                           <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                             <path stroke-linecap="round" stroke-linejoin="round" d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                           </svg>
                           Up one level
                        </a>'''
    
    return templates.TemplateResponse("repo_contents.html", {
        "request": request,
        "repo_full_name": escape_html_chars(f"{owner}/{repo_name}"),
        "current_path_display": escape_html_chars(current_path_unquoted if current_path_unquoted else "(root)"),
        "up_link": up_link_html,
        "content_list_html_items": content_list_html_items, # Renamed from content_list
        "error_message": error_message_for_template,
        "app_title": APP_TITLE
    })

@app.get("/repo/{owner}/{repo_name}/file", response_class=HTMLResponse)
async def view_single_file_content(
    request: Request, owner: str, repo_name: str,
    path: str = Query(...), github_pat: Optional[str] = Cookie(None)
):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    file_path_unquoted = unquote(path)
    parent_dir_path = os.path.dirname(file_path_unquoted)
    file_name_only = os.path.basename(file_path_unquoted)
    
    parent_contents_result = fetch_repo_contents_list(github_pat, owner, repo_name, parent_dir_path)
    
    error_message_for_template = None
    file_content_display_html = "" 
    is_binary_msg = False


    if parent_contents_result["error"]:
        error_message_for_template = f'Error fetching parent directory: {escape_html_chars(parent_contents_result["error"])}'
    else:
        file_item = next((item for item in parent_contents_result.get("data", []) 
                          if item.get("name") == file_name_only and item.get("type") == "file"), None)
        if not file_item or not file_item.get("download_url"):
            error_message_for_template = f'File "{escape_html_chars(file_name_only)}" not found in directory or no download URL available.'
        else:
            download_url = file_item.get("download_url")
            content_result = fetch_raw_file_content_from_url(github_pat, download_url)
            if content_result["error"]:
                error_message_for_template = escape_html_chars(content_result["error"])
            elif content_result.get("is_binary"): 
                is_binary_msg = True
                file_content_display_html = f"<p class='italic text-slate-500'>Binary file content cannot be displayed directly. <a href='{escape_html_chars(download_url)}' target='_blank' class='text-brand-blue hover:underline font-medium'>Download file</a>.</p>"
            else:
                file_content_display_html = escape_html_chars(content_result.get('data', ''))
    
    return templates.TemplateResponse("file_view.html", {
        "request": request,
        "file_path_display": escape_html_chars(file_path_unquoted),
        "repo_full_name": escape_html_chars(f"{owner}/{repo_name}"),
        "error_message": error_message_for_template,
        "back_to_dir_link": f'/repo/{owner}/{repo_name}?path={quote(parent_dir_path)}',
        "file_content_display_html": file_content_display_html, 
        "is_binary_file_message": is_binary_msg, # Pass this flag to the template
        "app_title": APP_TITLE
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
            "request": request, "message": message, "cv_entries_html_parts": [], "app_title": APP_TITLE
        })

    all_fetched_repos = getattr(app.state, 'user_repos_cache', None)
    if not all_fetched_repos:
        fetch_result = fetch_user_repos(github_pat)
        if fetch_result["error"] or not fetch_result["data"]:
            message = f'Could not fetch repositories for CV generation: {escape_html_chars(fetch_result.get("error", "No data"))}'
            return templates.TemplateResponse("cv_summary.html", {"request": request, "message": message, "cv_entries_html_parts": [], "app_title": APP_TITLE})
        all_fetched_repos = fetch_result["data"]
        app.state.user_repos_cache = all_fetched_repos

    repos_to_actually_process = []
    if action_type == 'manual_select':
        if not selected_repo_names:
            message = "No repositories were selected for manual processing."
            return templates.TemplateResponse("cv_summary.html", {"request": request, "message": message, "cv_entries_html_parts": [], "app_title": APP_TITLE})
        
        selected_repo_names_set = set(selected_repo_names)
        repos_to_actually_process = [repo for repo in all_fetched_repos if repo.get("full_name") in selected_repo_names_set]
        
        if len(repos_to_actually_process) > MAX_MANUAL_SELECT_REPOS_FOR_CV:
            message = f"Too many repositories selected. Please select no more than {MAX_MANUAL_SELECT_REPOS_FOR_CV}."
            return templates.TemplateResponse("cv_summary.html", {"request": request, "message": message, "cv_entries_html_parts": [], "app_title": APP_TITLE})

    elif action_type == 'auto_select':
        repos_to_actually_process = all_fetched_repos[:AUTO_SELECT_PROCESS_COUNT]
    else:
        message = "Invalid action type for CV generation."
        return templates.TemplateResponse("cv_summary.html", {"request": request, "message": message, "cv_entries_html_parts": [], "app_title": APP_TITLE})

    if not repos_to_actually_process:
        message = 'No repositories selected or available for CV summary processing.'
        return templates.TemplateResponse("cv_summary.html", {"request": request, "message": message, "cv_entries_html_parts": [], "app_title": APP_TITLE})

    print(f"Starting CV generation. Action: '{action_type}'. Repos to process: {[r.get('full_name') for r in repos_to_actually_process]}")
    generated_cvs_data = orchestrate_cv_generation_for_repos(github_pat, repos_to_actually_process, action_type)
    print("Finished CV generation orchestration.")

    cv_entries_html_result_parts = [] # Ensure this is initialized
    successful_cv_count = 0
    
    for cv_data in generated_cvs_data: 
        repo_name_esc = escape_html_chars(cv_data.get("repo", "Unknown Repo"))
        if cv_data.get("cv_entry"):
            successful_cv_count +=1
            cv_text_raw = cv_data["cv_entry"]
            cv_text_html = escape_html_chars(cv_text_raw).replace("\n", "<br />\n")
            cv_text_html = re.sub(r'\*\*(Project Description|Key Features|Technologies Used|Key Highlights):\*\*', r'<strong class="block mt-2 mb-1 text-slate-700">\1:</strong>', cv_text_html)
            cv_text_html = re.sub(r'(<br />\s*[\*\-]\s+)', r'<br /><span class="ml-4">• </span>', cv_text_html, flags=re.MULTILINE) # Added MULTILINE flag


            cv_entries_html_result_parts.append(f"""
            <article class="p-6 bg-slate-50 border border-slate-200 rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-200">
                <h3 class="text-xl font-semibold text-brand-indigo mb-3">{repo_name_esc}</h3>
                <div class="prose prose-sm max-w-none text-slate-600 leading-relaxed">
                    {cv_text_html}
                </div>
            </article>
            """)
        elif cv_data.get("error"):
            cv_entries_html_result_parts.append(f"""
            <article class="p-6 bg-red-50 border border-red-200 rounded-xl shadow-lg">
                <h3 class="text-xl font-semibold text-red-700 mb-3">{repo_name_esc}</h3>
                <p class="text-sm text-red-600">Could not generate CV entry: {escape_html_chars(cv_data["error"])}</p>
            </article>
            """)
    
    final_message_text = f"Finished processing. Attempted for {len(repos_to_actually_process)} repos. Displaying {successful_cv_count} CV entries."
    if successful_cv_count < len(generated_cvs_data) or len(generated_cvs_data) < len(repos_to_actually_process): # Check against generated_cvs_data which is post-filtering
         final_message_text += " Some errors occurred or fewer than attempted were selected for final display. Check server logs for details."
        
    return templates.TemplateResponse("cv_summary.html", {
        "request": request,
        "message": final_message_text,
        "cv_entries_html_parts": cv_entries_html_result_parts,
        "app_title": APP_TITLE
    })

# --- Main Execution ---
if __name__ == "__main__":
    if not getattr(uvicorn, 'run', None):
         print("uvicorn not found. Please ensure it's installed correctly.")
         print("To run: uvicorn main:app --reload --host 127.0.0.1 --port 8000")
    else:
        uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)