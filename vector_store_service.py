import numpy as np
import time

# Use the configured embedding dimension and service
from config import DEFAULT_EMBEDDING_DIMENSION
from gemini_service import get_embeddings_batch # This now routes to local or API based on config

# Attempt to import FAISS
try:
    import faiss
    print("FAISS library imported successfully.")
except ImportError:
    faiss = None
    print("FAISS library not found. Vector store functionality will be severely limited (basic keyword matching).")

class FAISSVectorStore:
    def __init__(self, dimension=DEFAULT_EMBEDDING_DIMENSION):
        if not faiss:
            self.index = None
            self.document_map = {} 
            self.next_id = 0
            print("FAISS not available. Using a simple list for documents (no actual vector search).")
            return

        self.dimension = dimension
        # Using IndexIDMap to map FAISS's internal sequential IDs to our own 'next_id'
        # This makes managing self.document_map slightly more straightforward with deletions/updates if needed.
        # For simple add-only, IndexFlatL2 is also fine, and IDs would be 0 to n-1.
        self.index = faiss.IndexIDMap(faiss.IndexFlatL2(dimension))
        self.document_map = {} # Stores {our_id: {"text": chunk_text, "repo_full_name": repo_full_name}}
        self.next_id = 0 # Counter for our custom IDs

    def add_documents(self, texts_with_repo_names: list[tuple[str, str]]):
        """
        Adds documents (chunks) to the FAISS index.
        texts_with_repo_names: list of tuples, e.g., [("chunk1 text", "owner/repo1"), ...]
        """
        if not self.index and faiss: 
            print("FAISS index not initialized properly. Cannot add documents.")
            return False
        
        texts_to_embed = [text for text, repo_name in texts_with_repo_names if text and text.strip()]
        repo_names_for_texts = [repo_name for text, repo_name in texts_with_repo_names if text and text.strip()]

        if not texts_to_embed:
            print("No valid texts to embed.")
            return False
            
        embedding_results = get_embeddings_batch(texts_to_embed) # Uses local or API based on config

        if embedding_results["error"] or not embedding_results.get("embeddings"):
            print(f"Failed to generate embeddings for batch: {embedding_results['error']}")
            return False
        
        embeddings_list = embedding_results["embeddings"]
        
        if len(embeddings_list) != len(texts_to_embed):
            print(f"Mismatch in number of embeddings ({len(embeddings_list)}) and texts ({len(texts_to_embed)}). Aborting add.")
            return False

        new_doc_ids_np = np.array([self.next_id + i for i in range(len(texts_to_embed))]).astype('int64')
        
        for i, text_chunk in enumerate(texts_to_embed):
            current_id = self.next_id + i
            self.document_map[current_id] = {"text": text_chunk, "repo_full_name": repo_names_for_texts[i]}
        
        self.next_id += len(texts_to_embed)

        if embeddings_list:
            embeddings_np = np.array(embeddings_list).astype('float32')
            if embeddings_np.shape[1] != self.dimension:
                print(f"ERROR: Embedding dimension mismatch! Expected {self.dimension}, got {embeddings_np.shape[1]}. Cannot add to FAISS.")
                # Rollback the IDs and document_map additions for this batch
                for i in range(len(texts_to_embed)):
                    self.document_map.pop(self.next_id - len(texts_to_embed) + i, None)
                self.next_id -= len(texts_to_embed)
                return False

            if faiss and self.index:
                self.index.add_with_ids(embeddings_np, new_doc_ids_np)
                print(f"Added {len(embeddings_list)} new documents to FAISS index. Total docs in index: {self.index.ntotal}")
            elif not faiss: # Fallback if FAISS is not available
                print(f"FAISS not available. Stored {len(texts_to_embed)} document texts in map (no vector indexing).")
            return True
        return False

    def search_relevant_chunks(self, query_text: str, repo_full_name_filter: str, k: int = 5):
        """
        Searches for k most relevant chunks for a given query text,
        filtered for a specific repository.
        """
        if not self.index and faiss:
            print("FAISS index not initialized. Cannot search.")
            return []
        if not query_text or not query_text.strip():
            return []

        query_embedding_result = get_embeddings_batch([query_text]) # Use batch for consistency
        if query_embedding_result["error"] or not query_embedding_result.get("embeddings"):
            print(f"Failed to generate query embedding: {query_embedding_result['error']}")
            return []

        query_vector = np.array(query_embedding_result["embeddings"]).astype('float32')
        if query_vector.shape[1] != self.dimension:
            print(f"ERROR: Query embedding dimension mismatch! Expected {self.dimension}, got {query_vector.shape[1]}.")
            return []
            
        relevant_chunks_text = []

        if faiss and self.index and self.index.ntotal > 0:
            # Search for more initially to allow for filtering by repo_full_name
            # k_search = min(self.index.ntotal, max(k * 5, 20)) # Heuristic
            # Search for all documents and filter in Python if repo_full_name_filter is specific
            # This is less efficient for very large NTotal, but simpler for filtering.
            # For true efficiency with filtering, FAISS metadata or separate indexes per repo would be better.
            
            # If we want to be more efficient, we'd need to iterate or use more complex FAISS features
            # For now, search k*N (N being rough number of repos if filtering is tight) or all if Ntotal is small
            k_search = min(self.index.ntotal, k * 10 if self.index.ntotal > k*10 else self.index.ntotal)


            distances, ids_from_faiss = self.index.search(query_vector, k_search)
            
            retrieved_count = 0
            for i in range(ids_from_faiss.shape[1]): 
                doc_id = ids_from_faiss[0, i]
                if doc_id == -1 : continue # FAISS can return -1 if fewer than k results are found

                if doc_id in self.document_map:
                    doc_info = self.document_map[doc_id]
                    if doc_info["repo_full_name"] == repo_full_name_filter:
                        relevant_chunks_text.append(doc_info["text"])
                        retrieved_count += 1
                        if retrieved_count >= k:
                            break
        elif not faiss: 
            print("FAISS not available. Performing basic keyword matching (very inefficient).")
            query_terms = set(query_text.lower().split())
            for doc_id_key, doc_info in self.document_map.items(): # Iterate our map
                if doc_info["repo_full_name"] == repo_full_name_filter:
                    doc_terms = set(doc_info["text"].lower().split())
                    # Simple keyword overlap - very basic relevance
                    if query_terms.intersection(doc_terms): 
                        relevant_chunks_text.append(doc_info["text"])
                        if len(relevant_chunks_text) >= k:
                            break
                            
        print(f"Found {len(relevant_chunks_text)} relevant chunks for query in '{repo_full_name_filter}'.")
        return relevant_chunks_text

    def reset_index(self):
        """Resets the FAISS index and document map."""
        if faiss and self.index:
            self.index.reset() # Resets the FAISS index itself
        self.document_map = {}
        self.next_id = 0
        print("Vector store index and document map have been reset.")

# Global instance of the vector store, initialized when this module is imported.
vector_store = FAISSVectorStore(dimension=DEFAULT_EMBEDDING_DIMENSION)

# --- Functions to save and load the vector store (basic implementation) ---
# In a real app, consider more robust serialization (e.g., joblib, or specific FAISS save/load for index)

FAISS_INDEX_FILE = "faiss_index.bin"
DOC_MAP_FILE = "doc_map.json" # Simple JSON for the document map

import json

def save_vector_store(vs_instance: FAISSVectorStore, index_path=FAISS_INDEX_FILE, map_path=DOC_MAP_FILE):
    if not faiss or not vs_instance.index:
        print("FAISS not available or index not initialized. Cannot save.")
        return
    try:
        print(f"Saving FAISS index to {index_path}...")
        faiss.write_index(vs_instance.index, index_path)
        
        print(f"Saving document map to {map_path}...")
        # Convert numpy int64 keys to int for JSON serialization if any exist
        serializable_doc_map = {int(k): v for k, v in vs_instance.document_map.items()}
        with open(map_path, 'w') as f:
            json.dump({"next_id": vs_instance.next_id, "document_map": serializable_doc_map}, f)
        print("Vector store saved successfully.")
    except Exception as e:
        print(f"Error saving vector store: {e}")

def load_vector_store(dimension=DEFAULT_EMBEDDING_DIMENSION, index_path=FAISS_INDEX_FILE, map_path=DOC_MAP_FILE):
    if not faiss:
        print("FAISS not available. Cannot load vector store.")
        return FAISSVectorStore(dimension=dimension) # Return a new, empty one

    loaded_vs = FAISSVectorStore(dimension=dimension) # Create instance first
    
    if os.path.exists(index_path) and os.path.exists(map_path):
        try:
            print(f"Loading FAISS index from {index_path}...")
            loaded_vs.index = faiss.read_index(index_path) # This replaces the index in loaded_vs
            
            print(f"Loading document map from {map_path}...")
            with open(map_path, 'r') as f:
                data = json.load(f)
                # Convert string keys back to int if JSON loads them as strings
                loaded_vs.document_map = {int(k): v for k, v in data.get("document_map", {}).items()}
                loaded_vs.next_id = data.get("next_id", 0)
            
            print(f"Vector store loaded successfully. Index has {loaded_vs.index.ntotal} documents. Map has {len(loaded_vs.document_map)} entries. Next ID: {loaded_vs.next_id}")
            # Crucial: ensure the global vector_store is this loaded instance
            global vector_store 
            vector_store = loaded_vs
            return loaded_vs
        except Exception as e:
            print(f"Error loading vector store: {e}. Returning a new, empty store.")
            # Fallback to a new store if loading fails
            vector_store.reset_index() # Ensure the global one is also reset
            return FAISSVectorStore(dimension=dimension) 
    else:
        print("No saved vector store found. Returning a new, empty store.")
        return loaded_vs # Return the new, empty one created at the start
