import time
import google.generativeai as genai
import asyncio # Import asyncio for async sleep

from config import (
    GOOGLE_API_KEY, 
    GENERATION_MODEL_NAME, 
    GEMINI_API_GENERATION_DELAY_SECONDS,
    USE_LOCAL_EMBEDDINGS, 
    GEMINI_EMBEDDING_MODEL_NAME 
)
from local_embedding_service import generate_single_local_embedding, generate_local_embeddings_batch


gemini_generation_configured = False
if GOOGLE_API_KEY and genai:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        print("Google Generative AI SDK configured for generation.")
        gemini_generation_configured = True
    except Exception as e:
        print(f"Error configuring Google Generative AI SDK: {e}. Gemini generation features may be disabled.")
elif not genai:
    print("Google Generative AI SDK (google-generativeai) not imported. Gemini features will be disabled.")
else: 
    print("GOOGLE_API_KEY not found. Gemini features will be disabled.")


def get_embedding(text_content: str):
    """Wrapper function to get embedding, using local or Gemini API based on config."""
    if USE_LOCAL_EMBEDDINGS:
        # Local embeddings are typically fast and don't need async sleep here
        return generate_single_local_embedding(text_content)
    else:
        # This part is for Gemini API embeddings
        if not gemini_generation_configured: 
            return {"error": "Gemini SDK not available or configured for API embeddings.", "embedding": None}
        if not text_content or not text_content.strip():
            return {"error": "Cannot generate embedding for empty text.", "embedding": None}

        print(f"Generating embedding via Gemini API for text snippet (len: {len(text_content)})...")
        # Apply delay for Gemini Embedding API calls as well if needed, though usually less strict than generation
        # time.sleep(GEMINI_API_GENERATION_DELAY_SECONDS) # Usually not needed for embeddings, but consider if rate limited
        try:
            result = genai.embed_content(
                model=GEMINI_EMBEDDING_MODEL_NAME,
                content=text_content,
                task_type="RETRIEVAL_DOCUMENT"
            )
            return {"error": None, "embedding": result['embedding']}
        except Exception as e:
            print(f"Error generating Gemini API embedding: {e}")
            return {"error": str(e), "embedding": None}

def get_embeddings_batch(texts: list[str]):
    """Wrapper function to get embeddings for a batch, using local or Gemini API."""
    if USE_LOCAL_EMBEDDINGS:
        return generate_local_embeddings_batch(texts)
    else:
        # Simplified batching with Gemini API (sequential sync calls)
        embeddings_list = []
        errors_list = []
        for text_idx, text in enumerate(texts):
            # Consider adding a small delay here if making many sequential API calls for embeddings
            # if text_idx > 0: time.sleep(1) # Example: 1 sec delay between embedding calls
            result = get_embedding(text) 
            if result["error"]:
                errors_list.append(f"Text {text_idx+1}: {result['error']}")
                # Optionally, append a None or a zero vector if you need to maintain list length
                # embeddings_list.append(None) 
            elif result["embedding"]:
                embeddings_list.append(result["embedding"])
            else: # Should not happen if error/embedding is always present
                errors_list.append(f"Text {text_idx+1}: Unknown error during embedding.")
        
        if errors_list:
            # If some embeddings failed but others succeeded, return partial results
            # The caller (vector_store_service) needs to handle this (e.g. skip docs that failed embedding)
            return {"error": f"Some errors occurred during Gemini API batch embedding: {'; '.join(errors_list)}", "embeddings": embeddings_list or None}
        return {"error": None, "embeddings": embeddings_list}


def generate_text_from_prompt(prompt: str, safety_settings=None):
    """Generates text from a given prompt using a Gemini generative model."""
    if not gemini_generation_configured:
        return {"error": "Gemini SDK not available or configured for generation.", "text": None}

    print(f"Generating text with Gemini model: {GENERATION_MODEL_NAME} (Prompt length: {len(prompt)} chars)...")
    time.sleep(GEMINI_API_GENERATION_DELAY_SECONDS) 
    
    try:
        model = genai.GenerativeModel(GENERATION_MODEL_NAME)
        
        if safety_settings is None:
             safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
        
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        generated_text = ""
        if response.parts: 
             generated_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
        
        # Check for block reason even if parts exist, as sometimes partial text might be returned before a block.
        if response.prompt_feedback and response.prompt_feedback.block_reason:
             block_reason_message = response.prompt_feedback.block_reason_message or f"Content blocked by safety filter ({response.prompt_feedback.block_reason})."
             print(f"Gemini content generation blocked. Reason: {response.prompt_feedback.block_reason}, Message: {block_reason_message}")
             # If text was generated before block, decide if to return it or just the error.
             # For CV, a partial/blocked entry is likely not useful.
             return {"error": block_reason_message, "text": None} # Prioritize block error
        
        if generated_text:
            return {"error": None, "text": generated_text}
        
        # If no text and not explicitly blocked, it's an unusual empty response.
        print(f"Gemini response was empty or unexpectedly formatted. Full response: {response}")
        return {"error": "Gemini response was empty or malformed (no text parts found and not blocked).", "text": None}

    except Exception as e:
        print(f"Error generating text with Gemini: {e}")
        error_message = str(e)
        if hasattr(e, 'message') and e.message: # type: ignore
            error_message = f"Gemini API Error: {e.message}" # type: ignore
        return {"error": error_message, "text": None}


def generate_cv_entry_for_project(project_name: str, context_chunks: list[str]):
    """
    Generates a CV-style entry for a project using Gemini, based on provided context.
    This function remains synchronous.
    """
    if not context_chunks:
        print(f"Warning: No context chunks provided for project {project_name}. AI will be informed in the prompt.")
        # The prompt is designed to handle "Information not available"
        context_str = "No specific code snippets or documentation were retrieved for context for this project."
    else:
        context_str = "\n---\n".join(context_chunks)
    
    prompt = f"""
    You are an expert technical writer specializing in crafting concise and impactful CV entries for software projects. Your goal is to describe the user's GitHub project '{project_name}' based ONLY on the provided code and documentation snippets (context).

    Create a professional CV entry with the following structure and content requirements. Use clear Markdown formatting.

    **CV Entry Structure:**

    **Project Title:** {project_name}

    **Project Overview:**
    Provide a brief (1-2 sentences) summary of the project's main purpose, goal, or what it achieves. Focus on its core function.

    **Key Technical Features & Accomplishments:**
    List 2-4 significant technical features, challenges overcome, or notable accomplishments demonstrated in the codebase. Be specific and quantify impact if possible (e.g., "Implemented a custom parser...", "Achieved X% performance improvement..."). Extract these directly from the context. Use markdown list formatting (- or *).

    **Technologies Used:**
    List the primary programming languages, significant frameworks, key libraries, and important tools explicitly mentioned or strongly evident from the context. Be specific (e.g., "Python (FastAPI)", "React with Redux", "PostgreSQL", "Docker"). Use markdown list formatting (- or *).

    **Important Constraints:**
    - Generate ONLY the CV entry text in Markdown format. Do not include any conversational text, introductions, or conclusions outside the entry structure.
    - Rely STRICTLY on the provided context. Do not invent features, technologies, or details.
    - If information for a section is genuinely not present or clearly inferable from the context, state "Information not available in provided context." for that specific section. If the entire context is empty or states no information, make this clear in the overview and other sections.
    - Prioritize technical depth and relevance for a developer's CV.
    - Keep sentences concise and professional.

    Context from project '{project_name}':
    ---
    {context_str}
    ---

    Generate the CV entry now for '{project_name}', following the structure and constraints:
    """

    print(f"Generating CV entry for {project_name} using provided context (context length: {len(context_str)} chars)...")
    generation_result = generate_text_from_prompt(prompt)
    
    # Adapt to the expected {"cv_entry": ..., "error": ...} structure
    return {
        "cv_entry": generation_result.get("text"), 
        "error": generation_result.get("error")
    }

