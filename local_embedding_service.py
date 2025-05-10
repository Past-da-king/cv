from sentence_transformers import SentenceTransformer
import numpy as np
import time # For potential delays if batch processing is very intensive

from config import LOCAL_EMBEDDING_MODEL_NAME, LOCAL_EMBEDDING_BATCH_SIZE

# Load the Sentence Transformer model globally on module import
# This means it's loaded once when the application starts.
try:
    print(f"Loading local Sentence Transformer model: {LOCAL_EMBEDDING_MODEL_NAME}...")
    # Consider adding device='cpu' if you want to be explicit, though it's default
    local_embedder_model = SentenceTransformer(LOCAL_EMBEDDING_MODEL_NAME)
    print(f"Local model '{LOCAL_EMBEDDING_MODEL_NAME}' loaded successfully.")
except Exception as e:
    local_embedder_model = None
    print(f"CRITICAL ERROR: Failed to load local Sentence Transformer model '{LOCAL_EMBEDDING_MODEL_NAME}'. Local embeddings will not work. Error: {e}")

def generate_local_embeddings_batch(texts: list[str]):
    """
    Generates embeddings locally for a batch of texts using Sentence Transformers.
    """
    if not local_embedder_model:
        return {"error": f"Local embedding model '{LOCAL_EMBEDDING_MODEL_NAME}' not loaded.", "embeddings": None}
    if not texts or not all(isinstance(t, str) for t in texts):
        return {"error": "Input must be a non-empty list of strings.", "embeddings": None}

    print(f"Generating local embeddings for a batch of {len(texts)} texts...")
    try:
        # The encode method can take a list of sentences.
        # convert_to_numpy=True is default, returns ndarray.
        embeddings_np = local_embedder_model.encode(texts, batch_size=LOCAL_EMBEDDING_BATCH_SIZE, show_progress_bar=False)
        # Convert to list of lists for easier handling / JSON if needed
        return {"error": None, "embeddings": embeddings_np.tolist()}
    except Exception as e:
        print(f"Error generating local embeddings batch: {e}")
        return {"error": str(e), "embeddings": None}

def generate_single_local_embedding(text_content: str):
    """
    Generates embedding locally for a single text content.
    This is a convenience wrapper around the batch function.
    """
    if not text_content or not isinstance(text_content, str):
         return {"error": "Input must be a non-empty string.", "embedding": None}
    
    result = generate_local_embeddings_batch([text_content])
    if result["error"] or not result["embeddings"]:
        return {"error": result["error"] or "Embedding generation failed.", "embedding": None}
    return {"error": None, "embedding": result["embeddings"][0]}

