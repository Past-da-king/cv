import time
from typing import Optional, List 
import asyncio # Import asyncio for async generator
from github_service import get_consolidated_repo_text_for_context
from gemini_service import generate_cv_entry_for_project # Correct import
from vector_store_service import vector_store # Use the global instance
from utils import simple_chunk_text
from config import (
    TEXT_CHUNK_SIZE_CHARS, TEXT_CHUNK_OVERLAP_CHARS,
    MAX_CONTEXT_CHUNKS_FOR_GEMINI_CV_GENERATION,
    AUTO_SELECT_FINAL_OUTPUT_COUNT,
    GEMINI_API_GENERATION_DELAY_SECONDS, # Used inside gemini_service
)

# Make the orchestration function an async generator
async def orchestrate_cv_generation_for_repos(token: str, repos_to_process: list[dict], action_type: str):
    """
    Orchestrates the CV generation for a list of repositories, yielding progress updates.
    `repos_to_process` is a list of repo dicts from GitHub API.
    `action_type` is 'manual_select' or 'auto_select'.
    This is an async generator function.
    """
    # Reset vector store at the start of a new process
    # This call is synchronous, but typically fast.
    await asyncio.to_thread(vector_store.reset_index)
    print("Session vector store reset for new CV generation request.")

    # Yield initial status
    total_repos = len(repos_to_process)
    yield {"type": "status", "status": "started", "total": total_repos, "message": f"Starting CV generation for {total_repos} repositories..."}
    await asyncio.sleep(0.1) 

    processed_results_for_filtering = [] # To store results for final selection (especially for auto)

    for i, repo_data in enumerate(repos_to_process):
        repo_full_name = repo_data.get("full_name")
        owner = repo_data.get("owner", {}).get("login")
        repo_name_only = repo_data.get("name")
        pushed_at = repo_data.get("pushed_at") 

        if not repo_full_name or not owner or not repo_name_only:
            err_msg = f"Skipped repo '{repo_data.get('name', 'Unknown Repo')}': Missing identifying information."
            print(err_msg)
            yield {"type": "status", "status": "error", "repo": repo_data.get('name', 'Unknown Repo'), "message": err_msg}
            processed_results_for_filtering.append({"repo": repo_data.get('name', 'Unknown Repo'), "cv_entry": None, "error": err_msg, "pushed_at": pushed_at})
            await asyncio.sleep(0.1)
            continue
        
        repo_display_name = f"{owner}/{repo_name_only}"
        step_prefix = f"[{i+1}/{total_repos}] {repo_display_name}:"

        print(f"\n--- Processing repository {i+1}/{total_repos}: {repo_display_name} for CV ---")
        yield {"type": "status", "status": "processing_context", "repo": repo_display_name, "message": f"{step_prefix} Fetching and consolidating repository text..."}
        await asyncio.sleep(0.1)

        # get_consolidated_repo_text_for_context is synchronous
        repo_text_content = await asyncio.to_thread(
            get_consolidated_repo_text_for_context, token, owner, repo_name_only
        )
        
        if not repo_text_content:
            err_msg = f"{step_prefix} Failed to retrieve or consolidate text content for context."
            print(err_msg)
            yield {"type": "status", "status": "error", "repo": repo_display_name, "message": err_msg}
            processed_results_for_filtering.append({"repo": repo_display_name, "cv_entry": None, "error": err_msg, "pushed_at": pushed_at})
            await asyncio.sleep(0.1)
            continue
        
        yield {"type": "status", "status": "processing_context", "repo": repo_display_name, "message": f"{step_prefix} Chunking text and adding to vector store..."}
        # Chunk the text
        text_chunks = simple_chunk_text(
            repo_text_content,
            TEXT_CHUNK_SIZE_CHARS,
            TEXT_CHUNK_OVERLAP_CHARS
        )

        if not text_chunks:
            err_msg = f"{step_prefix} No text chunks generated from repository content. Cannot create embeddings."
            print(err_msg)
            yield {"type": "status", "status": "error", "repo": repo_display_name, "message": err_msg}
            processed_results_for_filtering.append({"repo": repo_display_name, "cv_entry": None, "error": err_msg, "pushed_at": pushed_at})
            await asyncio.sleep(0.1)
            continue
        
        # Add chunks to vector store (this is also synchronous internally)
        docs_to_add_to_store = [(chunk, repo_display_name) for chunk in text_chunks]
        added_to_vs_ok = await asyncio.to_thread(vector_store.add_documents, docs_to_add_to_store)

        if not added_to_vs_ok:
            err_msg = f"{step_prefix} Failed to add document chunks to vector store."
            print(err_msg)
            yield {"type": "status", "status": "error", "repo": repo_display_name, "message": err_msg}
            processed_results_for_filtering.append({"repo": repo_display_name, "cv_entry": None, "error": err_msg, "pushed_at": pushed_at})
            await asyncio.sleep(0.1)
            continue
        
        yield {"type": "status", "status": "context_processed", "repo": repo_display_name, "message": f"{step_prefix} Context processed & embedded."}
        await asyncio.sleep(0.1)

        yield {"type": "status", "status": "generating_cv", "repo": repo_display_name, "message": f"{step_prefix} Retrieving relevant context and generating CV entry with AI..."}
        
        # Search relevant chunks (synchronous)
        # Using repo_display_name as query might be too broad. A more specific query could be better.
        # For now, this uses the repo name to find its own chunks.
        query_for_chunks = f"Summary of project {repo_display_name}"
        relevant_chunks = await asyncio.to_thread(
            vector_store.search_relevant_chunks,
            query_for_chunks,
            repo_display_name,  # Filter by this repo
            MAX_CONTEXT_CHUNKS_FOR_GEMINI_CV_GENERATION
        )

        if not relevant_chunks:
             yield {"type": "status", "status": "warning", "repo": repo_display_name, "message": f"{step_prefix} No specific context chunks found in vector store for CV generation. AI will generate based on project name only."}
        
        # generate_cv_entry_for_project is synchronous (Gemini SDK call, time.sleep)
        ai_cv_data = await asyncio.to_thread(
            generate_cv_entry_for_project, repo_display_name, relevant_chunks
        )
        
        # Construct the full result dictionary
        cv_result_dict = {
            "repo": repo_display_name,
            "pushed_at": pushed_at,
            "cv_entry": ai_cv_data.get("cv_entry"),
            "error": ai_cv_data.get("error")
        }
        processed_results_for_filtering.append(cv_result_dict)
        
        if cv_result_dict.get("cv_entry"):
            print(f"Successfully generated CV entry for {repo_display_name}.")
            yield {"type": "status", "status": "cv_generated", "repo": repo_display_name, "message": f"{step_prefix} CV entry generated successfully."}
        elif cv_result_dict.get("error"):
            print(f"Error generating CV entry for {repo_display_name}: {cv_result_dict['error']}")
            yield {"type": "status", "status": "error", "repo": repo_display_name, "message": f"{step_prefix} CV generation failed: {cv_result_dict['error']}"}
        
        await asyncio.sleep(0.1) # Small delay between repos

    # --- Final Processing/Filtering (for auto_select) ---
    final_cv_entries_for_display = []

    if action_type == 'auto_select':
        successful_entries = [
            entry for entry in processed_results_for_filtering 
            if entry.get("cv_entry") and entry.get("pushed_at")
        ]
        # Sort by pushed_at, ensuring a default for entries that might miss it (though unlikely now)
        successful_entries.sort(key=lambda x: x.get("pushed_at", "1970-01-01T00:00:00Z"), reverse=True)
        
        top_n_successful = successful_entries[:AUTO_SELECT_FINAL_OUTPUT_COUNT]
        
        # Get original list of repo full_names that were intended for processing in this batch
        # This ensures we report on all attempted, not just those with entries in processed_results_for_filtering
        processed_repo_full_names_list = [rdata.get("full_name") for rdata in repos_to_process]

        for repo_full_name_processed in processed_repo_full_names_list:
            # Find the result for this repo_full_name_processed
            result_entry = next((entry for entry in processed_results_for_filtering if entry.get("repo") == repo_full_name_processed), None)

            if result_entry:
                is_in_top_n = result_entry in top_n_successful # Check if this specific result object is in the top N list
                
                if is_in_top_n:
                    final_cv_entries_for_display.append(result_entry)
                elif result_entry.get("error"):
                    final_cv_entries_for_display.append(result_entry) 
                elif result_entry.get("cv_entry"): # It had a CV but wasn't in top N
                     final_cv_entries_for_display.append({
                        "repo": repo_full_name_processed,
                        "cv_entry": None, 
                        "error": f"Successfully processed but not selected among the top {AUTO_SELECT_FINAL_OUTPUT_COUNT} most recent with CVs.",
                        "pushed_at": result_entry.get("pushed_at")
                    })
                # else: # This case (result_entry exists but no cv_entry and no error) should be rare if logic is correct
                #      final_cv_entries_for_display.append({
                #         "repo": repo_full_name_processed,
                #         "cv_entry": None,
                #         "error": "Processed, but outcome unknown and not in top N.",
                #         "pushed_at": result_entry.get("pushed_at")
                #     })
            else: # Repo was in the input list, but no corresponding result_entry was found (should not happen)
                final_cv_entries_for_display.append({
                    "repo": repo_full_name_processed,
                    "cv_entry": None,
                    "error": "Processing outcome not recorded for this repository.",
                    "pushed_at": next((r.get("pushed_at") for r in repos_to_process if r.get("full_name") == repo_full_name_processed), None)
                })
    else: # manual_select
        final_cv_entries_for_display = processed_results_for_filtering

    yield {"type": "complete", "final_results": final_cv_entries_for_display, "message": "Processing complete. Click 'Back to Repositories' or wait for redirect."}

