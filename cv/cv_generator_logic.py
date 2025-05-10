import time
from typing import Optional, List 
from github_service import get_consolidated_repo_text_for_context
from gemini_service import generate_cv_entry_for_project
from vector_store_service import vector_store # Use the global instance
from utils import simple_chunk_text
from config import (
    TEXT_CHUNK_SIZE_CHARS, TEXT_CHUNK_OVERLAP_CHARS,
    MAX_CONTEXT_CHUNKS_FOR_GEMINI_CV_GENERATION,
    AUTO_SELECT_FINAL_OUTPUT_COUNT
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
        pushed_at = repo_data.get("pushed_at") 

        if not repo_full_name or not owner or not repo_name_only:
            print(f"Skipping repo due to missing data: {repo_data.get('name', 'Unknown Repo')}")
            err_msg = f"Skipped repo '{repo_data.get('name', 'Unknown Repo')}': Missing identifying information."
            overall_status["errors"].append(err_msg)
            processed_repo_cv_data.append({"repo": repo_data.get('name', 'Unknown Repo'), "cv_entry": None, "error": err_msg, "pushed_at": pushed_at})
            continue
        
        print(f"\n--- Processing repository {i+1}/{len(repos_to_process)}: {repo_full_name} for CV ---")
        
        processed_ok = process_repo_for_cv_context(token, owner, repo_name_only)
        
        if not processed_ok:
            error_msg = f"Failed to process and embed context for {repo_full_name}."
            print(error_msg)
            processed_repo_cv_data.append({"repo": repo_full_name, "cv_entry": None, "error": error_msg, "pushed_at": pushed_at})
            overall_status["errors"].append(error_msg)
            time.sleep(0.5) 
            continue
        
        overall_status["processed_repos_for_context"] += 1
        
        cv_result = generate_cv_summary_for_repo(repo_full_name, pushed_at)
        processed_repo_cv_data.append(cv_result) # Store all processed results
        
        # Always add error to overall_status if CV generation itself failed
        if cv_result.get("error"):
            # Avoid adding "No contextual information found." if context processing already logged an error.
            # The more specific error from context processing is usually more helpful.
            # This check is imperfect but aims to reduce redundancy.
            context_processing_error_msg = f"Failed to process and embed context for {repo_full_name}."
            if not (cv_result["error"] == "No contextual information found." and context_processing_error_msg in overall_status["errors"]):
                 overall_status["errors"].append(f"CV Generation Error for {repo_full_name}: {cv_result['error']}")

    # Filter and sort for auto_select, or use all for manual_select
    if action_type == 'auto_select':
        # Filter for entries that have a CV and pushed_at date (for sorting)
        successful_entries = [
            entry for entry in processed_repo_cv_data 
            if entry.get("cv_entry") and entry.get("pushed_at")
        ]
        # Sort by pushed_at date (descending - most recent first)
        # Ensure pushed_at is not None before sorting, though prior filter should handle this
        successful_entries.sort(key=lambda x: x.get("pushed_at", "1970-01-01T00:00:00Z"), reverse=True)
        
        generated_cv_entries = successful_entries[:AUTO_SELECT_FINAL_OUTPUT_COUNT]
        overall_status["successful_cvs"] = len(generated_cv_entries)

    else: # manual_select
        generated_cv_entries = [entry for entry in processed_repo_cv_data if entry.get("cv_entry")]
        overall_status["successful_cvs"] = len(generated_cv_entries)
        # For manual select, all processed_repo_cv_data items are considered for output,
        # so if they have an error, it's relevant. Errors are already collected above.

    print(f"\n--- CV Generation Orchestration Complete ---")
    print(f"Processed {overall_status['processed_repos_for_context']} repositories for context.")
    print(f"Final CV entries count: {overall_status['successful_cvs']}.")
    if overall_status["errors"]:
        print(f"Encountered {len(overall_status['errors'])} errors/issues during the process:")
        for err in overall_status["errors"]:
            print(f"  - {err}")
            
    # Return all processed data for manual, but only top N for auto.
    # The display logic in main.py will handle showing errors for items not in generated_cv_entries.
    # It's better to return all processed_repo_cv_data items so main.py can show errors for non-selected items if needed.
    # However, the current main.py iterates `generated_cvs_data = orchestrate_cv_generation_for_repos(...)`
    # and expects only the final entries + their errors.
    # So, we need to ensure `generated_cv_entries` for auto_select contains all attempts, with errors for those that failed or weren't top N.
    
    if action_type == 'auto_select':
        # For auto-select, we want to show results for AUTO_SELECT_PROCESS_COUNT repos,
        # some might be successful (top N), others might have errors.
        # `processed_repo_cv_data` already contains all results for the repos processed.
        # We select the top N *successful* ones for `generated_cv_entries`.
        # The `main.py` needs to iterate `processed_repo_cv_data` to show errors for those that failed.
        # Let's adjust `generated_cv_entries` to include the errors for non-topN or failed items in auto mode for simplicity with current main.py structure.

        # Create a list of final entries to return: top N successful + errors for the rest that were processed
        final_output_list = []
        successful_repo_names = {entry['repo'] for entry in generated_cv_entries} # these are the top N

        # Add the top N successful entries
        final_output_list.extend(generated_cv_entries)

        # Add error entries for those processed but not in top N, or that failed
        for entry in processed_repo_cv_data:
            if entry['repo'] not in successful_repo_names:
                if entry.get("error") and not entry.get("cv_entry"): # Only add if it's an error entry and not a successful one we skipped
                    final_output_list.append(entry)
                elif not entry.get("cv_entry") and not entry.get("error"): # Case: processed, no CV, no error (e.g. no context)
                     final_output_list.append({
                        "repo": entry["repo"], 
                        "cv_entry": None, 
                        "error": entry.get("error", "Not selected for top output or no CV generated."), # Generic if no specific error
                        "pushed_at": entry.get("pushed_at")
                    })

        # Ensure the returned list for auto_select doesn't exceed AUTO_SELECT_PROCESS_COUNT in total items shown (success or error)
        # This is implicitly handled as `processed_repo_cv_data` is already limited by `AUTO_SELECT_PROCESS_COUNT`
        # The goal is to show *status* for all attempted in auto_select.
        # `main.py` iterates the returned list.
        # Let's just return `processed_repo_cv_data` directly if `action_type == 'auto_select'`
        # and let `main.py` handle presenting successful ones and errors from this list.
        # This simplifies logic here. `main.py` logic already handles this.
        if action_type == 'auto_select':
             # `main.py` will iterate this. If entry has "cv_entry", it's displayed as success.
             # If "error", it's displayed as error.
             # We need to ensure that if something was processed, got a CV, but wasn't in top N,
             # it still shows as "not selected" or similar.
             # The current main.py iterates `generated_cvs_data` and checks for `cv_entry` or `error`.

             # Let's rebuild generated_cv_entries for auto_select to be exactly what main.py expects
             # It should contain entries for *all* AUTO_SELECT_PROCESS_COUNT repos.
             # The top AUTO_SELECT_FINAL_OUTPUT_COUNT will have CVs, the rest will have an indication they weren't chosen or had errors.

            temp_generated_cv_entries = []
            # Add the successful top N
            top_n_successful = successful_entries[:AUTO_SELECT_FINAL_OUTPUT_COUNT]
            temp_generated_cv_entries.extend(top_n_successful)
            
            # For the remaining processed repos (up to AUTO_SELECT_PROCESS_COUNT), if they weren't in top_n_successful,
            # show their error or mark them as processed but not selected.
            processed_repo_names_in_auto_batch = {repo_data.get("full_name") for repo_data in repos_to_process} # these are the AUTO_SELECT_PROCESS_COUNT repos
            
            for entry in processed_repo_cv_data:
                is_in_top_n = any(top_entry['repo'] == entry['repo'] for top_entry in top_n_successful)
                if entry['repo'] in processed_repo_names_in_auto_batch and not is_in_top_n:
                    if entry.get("error"):
                        temp_generated_cv_entries.append(entry) # Already has an error
                    elif entry.get("cv_entry"): # Had a CV but wasn't top N
                        temp_generated_cv_entries.append({
                            "repo": entry["repo"],
                            "cv_entry": None, # Don't display CV
                            "error": f"Successfully processed but not selected among the top {AUTO_SELECT_FINAL_OUTPUT_COUNT}.",
                            "pushed_at": entry.get("pushed_at")
                        })
                    # else: it was processed, no CV, no error (e.g. no context) - main.py will show generic error if it iterates this.
                    # This case should already be covered by `generate_cv_summary_for_repo` returning an error.
            generated_cv_entries = temp_generated_cv_entries
            overall_status["successful_cvs"] = len(top_n_successful) # Count only truly successful & selected

    return generated_cv_entries

