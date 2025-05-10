import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# --- Google Gemini Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GENERATION_MODEL_NAME = 'gemini-2.0-flash-lite'

# --- Local Embedding Configuration ---
USE_LOCAL_EMBEDDINGS = True
LOCAL_EMBEDDING_MODEL_NAME = 'all-MiniLM-L6-v2'
DEFAULT_EMBEDDING_DIMENSION = 384

# --- GitHub Configuration ---
GITHUB_API_BASE_URL = "https://api.github.com"

# --- CV Generation & Processing Configuration ---
# Max repos to initially FETCH and display for user selection
MAX_REPOS_TO_DISPLAY_FOR_SELECTION = 50 # Adjust as needed, mindful of initial load

# For "Auto-Select Top N" feature:
# How many of the most recent repos to *process* (embed & send to Gemini)
AUTO_SELECT_PROCESS_COUNT = 5 # e.g., process the top 5
# From the processed repos, how many "best" CVs to actually *display*
AUTO_SELECT_FINAL_OUTPUT_COUNT = 3 # e.g., show the best 3 out of the 5 processed

# Max repos a user can manually select for processing at once
MAX_MANUAL_SELECT_REPOS_FOR_CV = 5 # To prevent overwhelming the system

GEMINI_API_GENERATION_DELAY_SECONDS = 5

MAX_FILE_SIZE_FOR_CONTEXT_BYTES = 100 * 1024
MAX_FILES_PER_REPO_FOR_CONTEXT = 5
MAX_CONSOLIDATED_TEXT_LENGTH_CHARS = 150000

TEXT_CHUNK_SIZE_CHARS = 1500
TEXT_CHUNK_OVERLAP_CHARS = 200

MAX_CONTEXT_CHUNKS_FOR_GEMINI_CV_GENERATION = 8

# --- Application Configuration ---
APP_TITLE = "GitHub CV Assistant"
APP_VERSION = "0.5.0"

# Only relevant if USE_LOCAL_EMBEDDINGS is False
GEMINI_EMBEDDING_MODEL_NAME = 'models/embedding-001' 

# Local Embedding Specific Configuration
LOCAL_EMBEDDING_BATCH_SIZE = 16
