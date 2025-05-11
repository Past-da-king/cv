import uvicorn
from fastapi import FastAPI, Request, Form, Query, Cookie, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates 
from typing import Optional, List, AsyncGenerator
import os
from urllib.parse import quote, unquote
import re 
import html as html_escaper 
import asyncio 
import uuid 
import json 
import requests 

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
    fetch_raw_file_content_from_url, get_github_api_headers 
)
from cv_generator_logic import orchestrate_cv_generation_for_repos 
from utils import escape_html_chars, markdown_to_html, format_github_api_error 
from vector_store_service import load_vector_store 
from local_embedding_service import local_embedder_model 

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

templates = Jinja2Templates(directory="templates") 
app.state.user_repos_cache = None 
app.state.processing_tasks = {} 


static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"Warning: Static directory not found at '{static_dir}'. Ensure it's correctly placed.")


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

async def get_github_pat(request: Request, github_pat: Optional[str] = Cookie(None)):
    return github_pat

@app.get("/", response_class=HTMLResponse)
async def get_token_form_page(request: Request, error: Optional[str] = None, github_pat: Optional[str] = Depends(get_github_pat)):
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
    
    headers = get_github_api_headers(token)
    try:
        response = await asyncio.to_thread(requests.get, f"{config.GITHUB_API_BASE_URL}/user", headers=headers, timeout=5)
        response.raise_for_status() 
        user_data = response.json()
        print(f"Successfully validated PAT for user: {user_data.get('login', 'Unknown')}")
    except requests.exceptions.RequestException as e:
        error_msg_detail = str(e)
        if isinstance(e, requests.exceptions.HTTPError):
            error_msg_detail = format_github_api_error(e)
        error_msg = quote(f"Invalid GitHub PAT or API error: {error_msg_detail}")
        print(f"PAT validation failed: {e}")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    response = RedirectResponse(url="/repos", status_code=303)
    response.set_cookie(
        key="github_pat", value=token, httponly=True, 
        samesite="lax", max_age=3600 * 24 * 7, 
        secure=request.url.scheme == "https", path="/"
    ) 
    return response

@app.get("/repos", response_class=HTMLResponse)
async def list_repositories_page(request: Request, github_pat: Optional[str] = Depends(get_github_pat), error: Optional[str] = None):
    if not github_pat:
        error_msg = quote("GitHub PAT not found or expired. Please enter it again to connect.")
        return RedirectResponse(url=f"/?error={error_msg}", status_code=303)

    if app.state.user_repos_cache is None:
        result = await asyncio.to_thread(fetch_user_repos, github_pat) 
        if result["error"]:
             error_message_for_template = f'{escape_html_chars(result["error"])} You might need to re-enter your token.'
             repos_to_display = [] 
             app.state.user_repos_cache = None 
        else:
            app.state.user_repos_cache = result["data"] 
            repos_to_display = result["data"][:MAX_REPOS_TO_DISPLAY_FOR_SELECTION] 
            error_message_for_template = unquote(error) if error else None 
    else:
        print("Using cached repository list.")
        repos_to_display = app.state.user_repos_cache[:MAX_REPOS_TO_DISPLAY_FOR_SELECTION]
        error_message_for_template = unquote(error) if error else None 

    repo_cards_html = ""
    if repos_to_display:
        card_items = []
        for repo in repos_to_display:
            repo_full_name = repo.get("full_name", "N/A")
            repo_full_name_escaped = escape_html_chars(repo_full_name)
            owner_login = escape_html_chars(repo.get("owner", {}).get("login", ""))
            repo_name_only = escape_html_chars(repo.get("name", ""))
            language = repo.get("language")
            language_escaped = escape_html_chars(language if language else "N/A")
            pushed_at_raw = repo.get("pushed_at", "N/A")
            pushed_at_date = pushed_at_raw[:10] if pushed_at_raw and pushed_at_raw != "N/A" else "N/A"
            pushed_at_escaped = escape_html_chars(pushed_at_date)
            visibility = repo.get("visibility", "N/A")
            visibility_escaped = escape_html_chars(visibility.capitalize())
            description_raw = repo.get("description") 
            description_escaped = escape_html_chars(description_raw[:120] + "..." if description_raw and len(description_raw) > 120 else description_raw or "No description provided.")
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
                </h3><p class="text-xs text-slate-500 mt-0.5">Last pushed: {pushed_at_escaped}</p>
            </div>
        </div><p class="text-sm text-slate-600 mb-4 h-16 overflow-hidden leading-relaxed">{description_escaped}</p> 
    </div>
    <div class="px-5 sm:px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
        <span class="inline-flex items-center gap-1.5"><span class="capitalize px-2 py-0.5 bg-slate-200 text-slate-700 rounded-full font-medium">{visibility_escaped}</span>
            {(f'<span class="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded-full font-medium">{language_escaped}</span>') if language else ''}</span>
        <span class="flex items-center gap-3"><span class="flex items-center" title="{star_count} stars"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-amber-400 mr-0.5"><path fill-rule="evenodd" d="M10.868 2.884c-.321-.772-1.415-.772-1.736 0l-1.83 4.401-4.753.393c-.83.069-.996 1.033-.464 1.491l3.493 3.01-1.057 4.637c-.19.825.743 1.44 1.482 1.06l4.116-2.512 4.116 2.512c.74.38 1.673-.235 1.482-1.06l-1.057-4.637 3.494-3.01c.531-.458.366-1.422-.464-1.491l-4.753-.393-1.83-4.401z" clip-rule="evenodd" /></svg>{star_count}</span>
            <span class="flex items-center" title="{fork_count} forks"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-slate-400 mr-0.5"><path fill-rule="evenodd" d="M10 2c-2.236 0-4.048.032-5.454.144C3.044 2.264 2 3.22 2 4.544v8.912c0 1.324 1.043 2.28 2.546 2.402C6.03 16.005 8.005 16 10 16s3.97-.005 5.454-.144c1.503-.122 2.546-1.078 2.546-2.402V4.544c0-1.324-1.043-2.28-2.546-2.402C13.969 2.032 12.236 2 10 2zM6.67 10.43a2.5 2.5 0 100-5 2.5 2.5 0 000 5zm6.66 0a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" clip-rule="evenodd" /></svg>{fork_count}</span>
        </span></div></div>''')
        repo_cards_html = "".join(card_items)
        
    return templates.TemplateResponse("repo_list.html", {
        "request": request, "error_message": error_message_for_template, "repo_cards_html": repo_cards_html,
        "max_manual_select_repos": MAX_MANUAL_SELECT_REPOS_FOR_CV, "auto_select_process_count": AUTO_SELECT_PROCESS_COUNT,
        "auto_select_output_count": AUTO_SELECT_FINAL_OUTPUT_COUNT, "app_title": APP_TITLE, "app_version": APP_VERSION,
    })

@app.get("/repo/{owner}/{repo_name}", response_class=HTMLResponse)
async def view_repo_directory_contents(request: Request, owner: str, repo_name: str, path: str = Query(""), github_pat: Optional[str] = Depends(get_github_pat)):
    if not github_pat: return RedirectResponse(url=f"/?error={quote('GitHub PAT not found or expired. Please connect again.')}", status_code=303)
    current_path_unquoted = unquote(path)
    result = await asyncio.to_thread(fetch_repo_contents_list, github_pat, owner, repo_name, current_path_unquoted)
    content_list_html_items, error_message_for_template = "", None
    if result["error"]: error_message_for_template = escape_html_chars(result["error"])
    elif result["data"]:
        items = []
        for item in result["data"]:
            item_name_escaped, item_path_raw, encoded_item_path, item_type = escape_html_chars(item.get("name", "N/A")), item.get("path", ""), quote(item.get("path", "")), item.get("type", "unknown")
            icon_svg, link_class, item_details = "", "font-medium text-slate-700 hover:text-primary-DEFAULT transition-colors group-hover:text-primary-DEFAULT", ""
            if item_type == "dir":
                icon_svg, link_target, item_details = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-amber-500 group-hover:text-amber-600 transition-colors"><path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" /></svg>''', f'/repo/{owner}/{repo_name}?path={encoded_item_path}', "<span class='text-xs text-slate-400'>Directory</span>"
            elif item_type == "file":
                icon_svg, link_target, item_details = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-slate-400 group-hover:text-slate-500 transition-colors"><path fill-rule="evenodd" d="M4 4a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2V8a2 2 0 00-2-2h-5L9 4H4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z" clip-rule="evenodd" /></svg>''', f'/repo/{owner}/{repo_name}/file?path={encoded_item_path}', f"<span class='text-xs text-slate-400'>{item.get('size',0)} bytes</span>"
            else: icon_svg, link_target, link_class, item_details = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-slate-400"><path fill-rule="evenodd" d="M12.207 2.207a1 1 0 011.414 0l4.25 4.25a1 1 0 010 1.414l-4.25 4.25a1 1 0 01-1.414-1.414L14.586 9H4.75a1 1 0 110-2h9.836L12.207 3.621a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg>''', "#", "text-slate-500 cursor-default", f"<span class='text-xs text-slate-400'>(type: {escape_html_chars(item_type)})</span>"
            items.append(f'''<li class="group"><a href="{link_target}" class="block hover:bg-slate-50 transition-colors"><div class="flex items-center justify-between px-4 py-4 sm:px-6"><div class="flex items-center min-w-0 space-x-3">{icon_svg}<p class="truncate text-sm {link_class}">{item_name_escaped}</p></div><div class="flex items-center space-x-3 ml-2">{item_details}<svg class="h-5 w-5 text-slate-400 group-hover:text-slate-500 transition-colors" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" /></svg></div></div></a></li>''')
        content_list_html_items = "".join(items)
    up_link_html = ""
    if current_path_unquoted: up_link_html = f'''<a href="/repo/{owner}/{repo_name}?path={quote(os.path.dirname(current_path_unquoted))}" class="inline-flex items-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm ring-1 ring-inset ring-slate-300 hover:bg-slate-50 transition-colors"><svg class="-ml-0.5 mr-1.5 h-5 w-5 text-slate-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd"></path></svg>Up one level</a>'''
    return templates.TemplateResponse("repo_contents.html", {"request": request, "repo_full_name": escape_html_chars(f"{owner}/{repo_name}"), "current_path_display": escape_html_chars(current_path_unquoted or "(root)"), "up_link": up_link_html, "content_list_html_items": content_list_html_items, "error_message": error_message_for_template, "app_title": APP_TITLE, "app_version": APP_VERSION})

@app.get("/repo/{owner}/{repo_name}/file", response_class=HTMLResponse)
async def view_single_file_content(request: Request, owner: str, repo_name: str, path: str = Query(...), github_pat: Optional[str] = Depends(get_github_pat)):
    if not github_pat: return RedirectResponse(url=f"/?error={quote('GitHub PAT not found or expired. Please connect again.')}", status_code=303)
    file_path_unquoted, error_message_for_template, file_content_display_html, is_binary_msg, download_url = unquote(path), None, "", False, None
    headers, encoded_file_path = get_github_api_headers(github_pat), quote(file_path_unquoted)
    file_url = f"{config.GITHUB_API_BASE_URL}/repos/{owner}/{repo_name}/contents/{encoded_file_path}"
    try:
        response = await asyncio.to_thread(requests.get, file_url, headers=headers, timeout=10); response.raise_for_status(); file_item_response = response.json()
        if isinstance(file_item_response, list) or file_item_response.get("type") != "file": error_message_for_template = f'Path "{escape_html_chars(file_path_unquoted)}" is not a regular file.'
        else: 
            download_url = file_item_response.get("download_url")
            if not download_url: # Corrected assignment for error message
                 error_message_for_template = f'File "{escape_html_chars(os.path.basename(file_path_unquoted))}" found, but no download URL.'
    except requests.exceptions.HTTPError as e: error_message_for_template = format_github_api_error(e)
    except requests.exceptions.RequestException as e: error_message_for_template = f"Request failed: {e}"
    except json.JSONDecodeError: error_message_for_template = "Failed to parse API response."
    if download_url:
        content_result = await asyncio.to_thread(fetch_raw_file_content_from_url, github_pat, download_url)
        if content_result["error"]: error_message_for_template = (error_message_for_template + " | " if error_message_for_template else "") + escape_html_chars(content_result["error"])
        elif content_result.get("is_binary"): is_binary_msg, file_content_display_html = True, f"<p class='italic text-slate-500'>Binary file content cannot be displayed. <a href='{escape_html_chars(download_url)}' target='_blank' rel='noopener noreferrer' class='text-primary-DEFAULT hover:underline font-medium'>Download file</a>.</p>"
        else: file_content_display_html = escape_html_chars(content_result.get('data', ''))
    return templates.TemplateResponse("file_view.html", {"request": request, "file_path_display": escape_html_chars(file_path_unquoted), "repo_full_name": escape_html_chars(f"{owner}/{repo_name}"), "error_message": error_message_for_template, "back_to_dir_link": f'/repo/{owner}/{repo_name}?path={quote(os.path.dirname(file_path_unquoted))}', "file_content_display_html": file_content_display_html, "is_binary_file_message": is_binary_msg, "app_title": APP_TITLE, "app_version": APP_VERSION})

@app.post("/generate-cv-summary")
async def initiate_cv_generation(request: Request, github_pat: Optional[str] = Depends(get_github_pat), action_type: str = Form(...), selected_repo_names: Optional[List[str]] = Form(None)):
    if not github_pat: return RedirectResponse(url=f"/?error={quote('GitHub PAT not found or expired. Please connect again.')}", status_code=303)
    if not GOOGLE_API_KEY: return RedirectResponse(url=f"/repos?error={quote('Google API Key not configured. CV generation feature is disabled.')}", status_code=303)
    if local_embedder_model is None and config.USE_LOCAL_EMBEDDINGS: return RedirectResponse(url=f"/repos?error={quote('Local embedding model failed to load. CV context building will not work.')}", status_code=303)
    
    all_fetched_repos = getattr(app.state, 'user_repos_cache', None)
    if not all_fetched_repos:
        fetch_result = await asyncio.to_thread(fetch_user_repos, github_pat)
        if fetch_result["error"] or not fetch_result["data"]:
            error_detail = escape_html_chars(fetch_result.get("error", "No data"))
            error_url = f"/repos?error={quote(f'Could not fetch repositories: {error_detail}')}"
            return RedirectResponse(url=error_url, status_code=303)
        all_fetched_repos = fetch_result["data"]
        app.state.user_repos_cache = all_fetched_repos
        
    repos_to_actually_process = []
    if action_type == 'manual_select':
        if not selected_repo_names: return RedirectResponse(url=f"/repos?error={quote('No repositories selected.')}", status_code=303)
        selected_repo_names_set = set(selected_repo_names)
        repos_to_actually_process = [repo for repo in all_fetched_repos if repo.get("full_name") in selected_repo_names_set]
        if len(repos_to_actually_process) > MAX_MANUAL_SELECT_REPOS_FOR_CV: return RedirectResponse(url=f"/repos?error={quote(f'Max {MAX_MANUAL_SELECT_REPOS_FOR_CV} repos for manual selection.')}", status_code=303)
    elif action_type == 'auto_select':
        sorted_repos = sorted(all_fetched_repos, key=lambda x: x.get("pushed_at", "1970-01-01T00:00:00Z"), reverse=True)
        repos_to_actually_process = sorted_repos[:AUTO_SELECT_PROCESS_COUNT]
    else: return RedirectResponse(url=f"/repos?error={quote('Invalid action type.')}", status_code=303)
    
    if not repos_to_actually_process: return RedirectResponse(url=f"/repos?error={quote('No repositories to process.')}", status_code=303)
    
    process_id = str(uuid.uuid4())
    app.state.processing_tasks[process_id] = {"token": github_pat, "repos": repos_to_actually_process, "action_type": action_type, "status": "pending", "results": None, "error_message": None}
    print(f"Initiated CV generation task {process_id} for {len(repos_to_actually_process)} repos.")
    return RedirectResponse(url=f"/cv-progress/{process_id}", status_code=303)

@app.get("/cv-progress/{process_id}", response_class=HTMLResponse)
async def show_cv_progress_page(request: Request, process_id: str):
    task_data = app.state.processing_tasks.get(process_id)
    if not task_data: return RedirectResponse(url=f"/repos?error={quote('Processing task not found or expired.')}", status_code=303)
    if task_data["status"] in ["complete", "error", "cancelled"]:
         final_summary_url = request.url_for('show_final_cv_summary_page', process_id=process_id)
         return RedirectResponse(url=final_summary_url, status_code=303)
    final_summary_url = request.url_for('show_final_cv_summary_page', process_id=process_id)
    return templates.TemplateResponse("cv_progress.html", {"request": request, "process_id": process_id, "final_summary_url": final_summary_url, "app_title": APP_TITLE, "app_version": APP_VERSION})


async def _cv_event_stream_generator(
    process_id: str, 
    github_pat_token: str, 
    app_state_tasks: dict 
) -> AsyncGenerator[str, None]:
    """Inner async generator for SSE events."""
    
    task_data = app_state_tasks.get(process_id) 

    if not github_pat_token: 
        yield f"data: {json.dumps({'type': 'error', 'message': 'Authentication context lost.'})}\n\n"
        yield f"event: end\ndata: Stream finished due to auth error.\n\n"
        return

    if not task_data: 
        yield f"data: {json.dumps({'type': 'error', 'message': 'Processing task data not found.'})}\n\n"
        yield f"event: end\ndata: Stream finished due to missing task data.\n\n"
        return
        
    if task_data["status"] in ["running", "complete", "error", "cancelled"]:
        yield f"data: {json.dumps({'type': task_data['status'], 'message': f'Process is already {task_data["status"]}.'})}\n\n"
        if task_data["status"] == "complete" and task_data.get("results") is not None:
             complete_event = {"type": "complete", "final_results": task_data["results"], "message": "Processing complete. Results available."}
             yield f"data: {json.dumps(complete_event)}\n\n"
        yield f"event: end\ndata: Stream finished as process already handled.\n\n"
        return 
        
    task_data["status"] = "running" 
    repos_to_process = task_data["repos"]
    action_type = task_data["action_type"]

    try:
        async for event in orchestrate_cv_generation_for_repos(github_pat_token, repos_to_process, action_type):
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "complete":
                task_data["results"] = event.get("final_results", []) 
                task_data["status"] = "complete"                     
            await asyncio.sleep(0.01) 

    except asyncio.CancelledError:
         print(f"Stream for process {process_id} cancelled (client disconnected).")
         task_data["status"] = "cancelled" 
         task_data["error_message"] = "Processing cancelled by client."
    except Exception as e:
        print(f"Error during SSE stream for process {process_id}: {e}")
        error_payload = {'type': 'error', 'message': f'An unexpected server error occurred: {str(e)}'}
        yield f"data: {json.dumps(error_payload)}\n\n"
        task_data["status"] = "error" 
        task_data["error_message"] = str(e) 
    finally:
         yield f"event: end\ndata: Stream finished.\n\n"
         print(f"SSE stream for process {process_id} ended with status: {task_data.get('status', 'unknown')}.")


@app.get("/cv-progress-stream/{process_id}")
async def stream_cv_progress(
    request: Request, 
    process_id: str, 
    github_pat: Optional[str] = Depends(get_github_pat)
):
    if not github_pat:
        raise HTTPException(status_code=401, detail="Authentication failed. GitHub PAT missing.")

    task_data = app.state.processing_tasks.get(process_id)
    if not task_data:
        raise HTTPException(status_code=404, detail="Processing task not found or expired.")
        
    event_generator = _cv_event_stream_generator(
        process_id=process_id,
        github_pat_token=github_pat, 
        app_state_tasks=app.state.processing_tasks 
    )
    return StreamingResponse(event_generator, media_type="text/event-stream")


@app.get("/cv-summary/{process_id}", response_class=HTMLResponse)
async def show_final_cv_summary_page(request: Request, process_id: str):
    task_data = app.state.processing_tasks.get(process_id)
    if not task_data: return RedirectResponse(url=f"/repos?error={quote(f'Task ID ''{process_id}'' not found.')}", status_code=303)
    status, error_detail = task_data.get("status"), task_data.get("error_message", "No specific error details.")
    if status not in ["complete"]:
         if status in ["running", "pending"]: return RedirectResponse(url=f"/cv-progress/{process_id}", status_code=303)
         error_msg = f"Task '{process_id}' status: {status}. " + (f"Details: {error_detail}" if error_detail and status in ["error", "cancelled"] else "Check progress or retry.")
         return RedirectResponse(url=f"/repos?error={quote(error_msg)}", status_code=303)
    generated_cvs_data, cv_entries_html_result_parts, successful_cv_count = task_data.get("results", []), [], 0
    for cv_data in generated_cvs_data: 
        repo_name_esc = escape_html_chars(cv_data.get("repo", "Unknown Repo"))
        if cv_data.get("cv_entry"):
            successful_cv_count +=1; cv_text_html = markdown_to_html(cv_data["cv_entry"]) 
            cv_entries_html_result_parts.append(f'''<article class="bg-white p-6 sm:p-8 rounded-xl shadow-xl border border-slate-200"><h3 class="text-xl font-semibold text-primary-DEFAULT mb-4">{repo_name_esc}</h3><div class="prose prose-slate max-w-none cv-content-body">{cv_text_html}</div></article>''')
        elif cv_data.get("error"):
            cv_entries_html_result_parts.append(f'''<article class="bg-red-50 p-6 sm:p-8 rounded-xl shadow-lg border border-red-200 text-red-700"><div class="flex items-start space-x-3"><svg class="flex-shrink-0 w-6 h-6 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m0-10.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.75c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.57-.598-3.75h-.152c-3.196 0-6.1-1.249-8.25-3.286zm0 13.036h.008v.008H12v-.008z" /></svg><div><h3 class="text-xl font-semibold mb-2">{repo_name_esc}</h3><p class="text-sm"><strong class="font-medium">Status/Error:</strong> {escape_html_chars(cv_data["error"])}</p></div></div></article>''')
    actual_processed_count, total_results_displayed = len(task_data.get("repos", [])), len(generated_cvs_data)
    final_message_text = f"Displaying results for {total_results_displayed} processed repositories ({successful_cv_count} successful CVs)."
    if total_results_displayed < actual_processed_count and task_data.get("action_type") == "auto_select": final_message_text += f" 'Auto-Select' attempted to process {actual_processed_count} repos."
    elif total_results_displayed == 0 and not error_detail: final_message_text = "No CV entries were successfully generated. All attempted repositories may have resulted in errors or no content."
    return templates.TemplateResponse("cv_summary.html", {"request": request, "message": final_message_text, "cv_entries_html_parts": cv_entries_html_result_parts, "app_title": APP_TITLE, "app_version": APP_VERSION})

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_module_path = "main:app"
    print(f"Running uvicorn for module: {app_module_path} from CWD: {script_dir}")
    reload_paths = [".", "templates", "static"]
    try:
        os.chdir(script_dir)
        uvicorn.run(app_module_path, host="127.0.0.1", port=8000, reload=True, reload_dirs=reload_paths)
    except ImportError as e:
        print(f"ImportError: {e}. Could not run uvicorn. Is it installed and in PATH?\nTry: pip install uvicorn[standard] fastapi jinja2 python-dotenv requests google-generativeai sentence-transformers faiss-cpu numpy markdown\nTo run manually from project root (directory containing 'cv'): uvicorn cv.main:app --reload --host 127.0.0.1 --port 8000 --reload-dir cv")
    except Exception as e:
        print(f"An error occurred: {e}")