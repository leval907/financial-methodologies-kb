"""
Configuration for RAG-based Agent B
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Get base directory
BASE_DIR = Path(__file__).parent.parent.parent.parent

# Load environment variables
load_dotenv(BASE_DIR / '.env.qdrant')
load_dotenv(BASE_DIR / '.env.arango')
load_dotenv(BASE_DIR / '.env')  # Fallback

class Config:
    """Configuration settings for RAG Agent B"""
    
    # Qdrant Settings
    QDRANT_HOST = os.getenv('QDRANT_HOST', 'localhost')
    QDRANT_PORT = int(os.getenv('QDRANT_PORT', 6333))
    QDRANT_GRPC_PORT = int(os.getenv('QDRANT_GRPC_PORT', 6334))
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY', None)
    
    # Embedding Settings
    REQUESTY_API_KEY = os.getenv('REQUESTY_API_KEY')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'openai/text-embedding-3-small')
    EMBEDDING_DIMENSIONS = int(os.getenv('EMBEDDING_DIMENSIONS', 1536))
    
    # Chunking Parameters
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 800))  # Increased for large files
    CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 100))  # Proportionally increased
    
    # ArangoDB Settings (reuse existing)
    ARANGO_HOST = os.getenv('ARANGO_HOST', 'localhost')
    ARANGO_PORT = int(os.getenv('ARANGO_PORT', 8529))
    ARANGO_USERNAME = os.getenv('ARANGO_USER', 'root')
    ARANGO_PASSWORD = os.getenv('ARANGO_PASSWORD', '')
    ARANGO_DATABASE = os.getenv('ARANGO_DB', 'fin_kb_method')
    
    # LLM Settings
    LLM_MODEL = 'alibaba/qwen3-max'
    LLM_TEMPERATURE = 0.3
    LLM_MAX_TOKENS = 4000
    
    # RAG Search Parameters
    TOP_K_CHUNKS = 100  # Number of chunks to retrieve per category (increased from 50)
    MIN_SIMILARITY = 0.3  # Minimum cosine similarity threshold (lowered for better recall)
    
    # Extraction Categories
    CATEGORIES = ['stages', 'tools', 'indicators', 'rules']
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent.parent.parent
    WORK_DIR = BASE_DIR / 'work'
    PROMPTS_DIR = Path(__file__).parent / 'stage2_extraction' / 'prompts'
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        assert cls.REQUESTY_API_KEY, "REQUESTY_API_KEY not set in .env.qdrant"
        if not cls.ARANGO_PASSWORD:
            print("⚠️  Warning: ARANGO_PASSWORD not set (Stage 3 will be skipped)")
        return True

# Validate on import
Config.validate()
