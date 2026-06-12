from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config.settings import settings
from backend.utils.logging_config import logger

def setup_cors(app: FastAPI):
    """Configures production-safe CORS origins based on environment settings."""
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    
    # Load primary production URL
    if settings.FRONTEND_URL and settings.FRONTEND_URL not in origins:
        origins.append(settings.FRONTEND_URL)
        
    # Append local development routes if in development mode
    if settings.ENVIRONMENT == "development":
        origins.extend([
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080"
        ])
    origins = list(dict.fromkeys(origins))
        
    logger.info(f"Setting up CORS origins: {origins}")
    
    app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # ← was True, causes strict CORS enforcement
    allow_methods=["*"],
    allow_headers=["*"],
)
