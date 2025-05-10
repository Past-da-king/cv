import time
import google.generativeai as genai

# Configuration is now more centralized
from config import (
    GOOGLE_API_KEY, 
    GENERATION_MODEL_NAME, 
    GEMINI_API_GENERATION_DELAY_SECONDS,
    USE_LOCAL_EMBEDDINGS, # To decide if Gemini embedding function is even relevant
    GEMINI_EMBEDDING_MODEL_NAME # If using Gemini for embeddings
)
from local_embedding_service import generate_single_local_embedding, generate_local_embeddings_batch


# Initialize Gemini SDK for generation
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
else: # genai is imported but no API key
    print("GOOGLE_API_KEY not found. Gemini features will be disabled.")


def get_embedding(text_content: str):
    """
    Wrapper function to get embedding, using local or Gemini API based on config.
    """
    if USE_LOCAL_EMBEDDINGS:
        return generate_single_local_embedding(text_content)
    else:
        # This part is for Gemini API embeddings - less likely to be used with free tier limits
        if not gemini_generation_configured: # Re-use config check
            return {"error": "Gemini SDK not available or configured for API embeddings.", "embedding": None}
        if not text_content or not text_content.strip():
            return {"error": "Cannot generate embedding for empty text.", "embedding": None}

        print(f"Generating embedding via Gemini API for text snippet (len: {len(text_content)})...")
        # Note: Gemini API might have its own delays/rate limits different from generation
        time.sleep(GEMINI_API_GENERATION_DELAY_SECONDS) 
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
    """
    Wrapper function to get embeddings for a batch, using local or Gemini API.
    """
    if USE_LOCAL_EMBEDDINGS:
        return generate_local_embeddings_batch(texts)
    else:
        # Batching with Gemini API (less efficient than local batching due to API calls per item typically)
        # This is a simplified loop for Gemini API batching if needed.
        # A true batch endpoint for Gemini embeddings might exist or come in future.
        embeddings_list = []
        errors_list = []
        for text in texts:
            result = get_embedding(text) # Calls the single embedding function
            if result["error"]:
                errors_list.append(result["error"])
            elif result["embedding"]:
                embeddings_list.append(result["embedding"])
        
        if errors_list:
            return {"error": f"Some errors occurred during Gemini API batch embedding: {'; '.join(errors_list)}", "embeddings": embeddings_list or None}
        return {"error": None, "embeddings": embeddings_list}


def generate_text_from_prompt(prompt: str, safety_settings=None):
    """Generates text from a given prompt using a Gemini generative model."""
    if not gemini_generation_configured:
        return {"error": "Gemini SDK not available or configured for generation.", "text": None}

    print(f"Generating text with Gemini model: {GENERATION_MODEL_NAME}...")
    time.sleep(GEMINI_API_GENERATION_DELAY_SECONDS) 
    try:
        model = genai.GenerativeModel(GENERATION_MODEL_NAME)
        # More permissive safety settings for prototyping, be mindful for production
        # Default (if None) is often quite restrictive.
        if safety_settings is None:
             safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
        
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # Check for valid response text
        if response.parts: # Check if parts exist
             generated_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
             if generated_text:
                return {"error": None, "text": generated_text}

        # Check for blocking reasons
        if response.prompt_feedback and response.prompt_feedback.block_reason:
             block_reason_message = response.prompt_feedback.block_reason_message or f"Content blocked by safety filter ({response.prompt_feedback.block_reason})."
             print(f"Gemini content generation blocked. Reason: {response.prompt_feedback.block_reason}, Message: {block_reason_message}")
             return {"error": block_reason_message, "text": None}
        
        # If no parts and no block reason, it might be an empty response or other issue
        print(f"Gemini response was empty or unexpectedly formatted. Full response: {response}")
        return {"error": "Gemini response was empty or malformed (no text parts found and not blocked).", "text": None}

    except Exception as e:
        print(f"Error generating text with Gemini: {e}")
        # Attempt to get more details if it's a google.api_core.exceptions.GoogleAPIError
        if hasattr(e, 'message'):
            return {"error": f"Gemini API Error: {e.message}", "text": None}
        return {"error": str(e), "text": None}


def generate_cv_entry_for_project(project_name: str, context_chunks: list[str]):
    """
    Generates a CV-style entry for a project using Gemini, based on provided context.
    """
    if not context_chunks:
        return {"error": f"No context provided for project {project_name}.", "cv_entry": None}

    context_str = "\n---\n".join(context_chunks)
    
    # Refined prompt for better structure and conciseness
    prompt = f"""
    You are an expert technical writer creating a CV entry for a software project named '{project_name}'.
    Based ONLY on the following provided context from the project's files, generate a concise and impactful CV entry.

    The CV entry MUST include these sections, clearly formatted:
    1. **Project Description:** A brief (1-2 sentences) overview of the project's main purpose and functionality.
    2. **Key Features/Accomplishments:** List 2-3 most significant technical features or achievements evident in the context. Be specific.
    3. **Technologies Used:** List the primary programming languages, frameworks, and key libraries explicitly mentioned or strongly implied by the context.

    **Important Instructions:**
    - Be factual and stick to information present in the provided context. Do not invent features or technologies.
    - Prioritize conciseness and impact.
    - If context is insufficient for a section, state "Information not available in provided context." for that section.

    Context from project '{project_name}':
    ---
    {context_str}
    ---

    Generate the CV entry now for '{project_name}':
    """
    print(f"Generating CV entry for {project_name} using provided context...")
    return generate_text_from_prompt(prompt)
