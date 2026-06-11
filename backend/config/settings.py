import os
from pathlib import Path
from dotenv import load_dotenv

# Load root .env variables
load_dotenv()

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings:
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # CORS Origin
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # Vector Database
    QDRANT_URL: str = os.getenv("QDRANT_URL", "")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    
    # LLMs Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # File Storage Settings
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", os.getenv("STORAGE_BACKEND", "local"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "15"))
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "docmind")
    
    # Directory paths
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
    LOGS_DIR: Path = BASE_DIR / "logs"
    CACHE_DIR: Path = DATA_DIR / "cache"
    
    # Document DB Tracking path
    DOCS_DB_PATH: Path = DATA_DIR / "documents.json"
    
    # Local Qdrant backup path
    QDRANT_LOCAL_PATH: Path = DATA_DIR / "qdrant_db"

    @classmethod
    def ensure_dirs_exist(cls):
        """Creates the necessary data, logging, and cache directories on startup."""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cls.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Instantiate settings singleton
settings = Settings()
settings.ensure_dirs_exist()
