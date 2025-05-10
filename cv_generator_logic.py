import time
from typing import Optional, List 
from github_service import get_consolidated_repo_text_for_context
from gemini_service import generate_cv_entry_for_project
from vector_store_service import vector_store # Use the global instance
from utils import simple_chunk_text
from config import (
    TEXT_CHUNK_SIZE_CHARS, TEXT_CHUNK_OVERLAP_CHARS,
    MAX_CONTEXT_CHUNKS_FOR_GEMINI_CV_GENERATION,
    AUTO_SELECT_FINAL_OUTPUT_COUNT # Added for "best N"
)

def process_repo_for_cv_context(token: str, owner: str, repo_name: str):
    """
    Fetches consolidated text for a repo, chunks it, and adds to the vector store.
    """
    print(f"Processing {owner}/{repo_name} for CV context...")
    repo_full_name = f"{owner}/{repo_name}"

    consolidated_text = get_consolidated_repo_text_for_context(token, owner, repo_name)
    
    if not consolidated_text:
        print(f"No text consolidated for {repo_full_name}. Skipping embedding.")
        return False

    print(f"Chunking consolidated text for {repo_full_name} (length: {len(consolidated_text)} chars)...")
    chunks = simple_chunk_text(consolidated_text, TEXT_CHUNK_SIZE_CHARS, TEXT_CHUNK_OVERLAP_CHARS)
    
    if not chunks:
        print(f"No text chunks generated after consolidation for {repo_full_name}.")
        return False
    
    print(f"Generated {len(chunks)} chunks for {repo_full_name}.")

    chunks_with_repo_name = [(chunk, repo_full_name) for chunk in chunks]
    
    print(f"Adding {len(chunks_with_repo_name)} chunks from {repo_full_name} to vector store...")
    success = vector_store.add_documents(chunks_with_repo_name)
    
    if success:
        print(f"Successfully processed and added context for {repo_full_name} to vector store.")
    else:
        print(f"Failed to add context for {repo_full_name} to vector store.")
    return success


def generate_cv_summary_for_repo(repo_full_name: str, repo_pushed_at: Optional[str] = None): # Add pushed_at for potential heuristic
    """
    Generates a CV summary for a single repository using context from the vector store.
    """
    print(f"Attempting to generate CV summary for {repo_full_name}...")
    query_for_context = f"Provide a detailed summary of the project '{repo_full_name}', including its main purpose, key technical features, and technologies used."
    
    context_chunks = vector_store.search_relevant_chunks(
        query_text=query_for_context,
        repo_full_name_filter=repo_full_name,
        k=MAX_CONTEXT_CHUNKS_FOR_GEMINI_CV_GENERATION
    )

    if not context_chunks:
        print(f"No relevant context found in vector store for {repo_full_name}. Cannot generate CV entry.")
        return {"repo": repo_full_name, "cv_entry": None, "error": "No contextual information found.", "pushed_at": repo_pushed_at}

    result = generate_cv_entry_for_project(repo_full_name, context_chunks)
    
    if result["error"]:
        print(f"Error generating CV entry for {repo_full_name}: {result['error']}")
        return {"repo": repo_full_name, "cv_entry": None, "error": result["error"], "pushed_at": repo_pushed_at}
    
    print(f"Successfully generated CV entry for {repo_full_name}.")
    return {"repo": repo_full_name, "cv_entry": result["text"], "error": None, "pushed_at": repo_pushed_at}


def orchestrate_cv_generation_for_repos(token: str, repos_to_process: list[dict], action_type: str):
    """
    Orchestrates the CV generation for a list of repositories.
    `repos_to_process` is a list of repo dicts from GitHub API.
    `action_type` is 'manual_select' or 'auto_select'.
    """
    generated_cv_entries = []
    overall_status = {"processed_repos_for_context": 0, "successful_cvs": 0, "errors": []}

    vector_store.reset_index() 
    print("Session vector store reset for new CV generation request.")

    processed_repo_cv_data = [] # To store data before "best N" selection for auto

    for i, repo_data in enumerate(repos_to_process):
        repo_full_name = repo_data.get("full_name")
        owner = repo_data.get("owner", {}).get("login")
        repo_name_only = repo_data.get("name")
        pushed_at = repo_data.get("pushed_at") # For "best N" heuristic

        if not repo_full_name or not owner or not repo_name_only:
            # ... (error handling as before) ...
            print(f"Skipping repo due to missing data: {repo_data.get('name', 'Unknown Repo')}")
            err_msg = f"Skipped repo '{repo_data.get('name', 'Unknown Repo')}': Missing identifying information."
            overall_status["errors"].append(err_msg)
            processed_repo_cv_data.append({"repo": repo_data.get('name', 'Unknown Repo'), "cv_entry": None, "error": err_msg, "pushed_at": pushed_at})
            continue
        
        print(f"\n--- Processing repository {i+1}/{len(repos_to_process)}: {repo_full_name} for CV ---")
        
        processed_ok = process_repo_for_cv_context(token, owner, repo_name_only)
        
        if not processed_ok:
            # ... (error handling as before) ...
            error_msg = f"Failed to process and embed context for {repo_full_name}."
            print(error_msg)
            processed_repo_cv_data.append({"repo": repo_full_name, "cv_entry": None, "error": error_msg, "pushed_at": pushed_at})
            overall_status["errors"].append(error_msg)
            time.sleep(0.5) 
            continue
        
        overall_status["processed_repos_for_context"] += 1
        
        cv_result = generate_cv_summary_for_repo(repo_full_name, pushed_at)
        processed_repo_cv_data.append(cv_result) # Store all processed results
        
        # Don't count successful_cvs yet if auto_select, will do after filtering
        if action_type == 'manual_select':
            if cv_result.get("cv_entry"):
                overall_status["successful_cvs"] += 1
            elif cv_result.get("error"):
                overall_status["errors"].append(f"CV Generation Error for {repo_full_name}: {cv_result['error']}")

    # If auto_select, filter down to the "best N" (e.g., top N by pushed_at among those with successful CVs)
    if action_type == 'auto_select':
        successful_entries = [entry for entry in processed_repo_cv_data if entry.get("cv_entry") and entry.get("pushed_at")]
        # Sort by pushed_at date (descending - most recent first)
        successful_entries.sort(key=lambda x: x["pushed_at"], reverse=True)
        
        generated_cv_entries = successful_entries[:AUTO_SELECT_FINAL_OUTPUT_COUNT]
        overall_status["successful_cvs"] = len(generated_cv_entries)

        # Add errors from any repo that didn't make it to successful_entries
        for entry in processed_repo_cv_data:
            if entry.get("error") and entry not in successful_entries : # If it had an error AND wasn't among the ones we might pick
                 if f"CV Generation Error for {entry['repo']}: {entry['error']}" not in overall_status["errors"] and \
                    f"Failed to process and embed context for {entry['repo']}." not in overall_status["errors"] and \
                    f"Skipped repo '{entry['repo']}': Missing identifying information." not in overall_status["errors"]:
                    overall_status["errors"].append(f"Error for {entry['repo']} (not in top {AUTO_SELECT_FINAL_OUTPUT_COUNT}): {entry['error']}")


    else: # manual_select
        generated_cv_entries = processed_repo_cv_data


    print(f"\n--- CV Generation Orchestration Complete ---")
    print(f"Processed {overall_status['processed_repos_for_context']} repositories for context.")
    print(f"Final CV entries count: {overall_status['successful_cvs']}.")
    if overall_status["errors"]:
        print(f"Encountered {len(overall_status['errors'])} errors/issues during the process.")
            
    return generated_cv_entries
