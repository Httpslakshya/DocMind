import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from backend.api.auth import router as auth_router
from backend.api.documents import router as documents_router, seed_documents
from backend.api.chat import router as chat_router
from backend.middleware.security import setup_cors
from backend.utils.logging_config import logger

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Executes lifecycle events, runs seeding pipelines on startup, and releases resources on shutdown."""
    logger.info("Starting up DocMind backend service...")
    try:
        # Run startup seeding for PDFs in Agentic_Ai/RAG
        seed_documents()
    except Exception as e:
        logger.error(f"Failed to seed files on startup: {e}", exc_info=True)
    yield
    logger.info("Shutting down DocMind backend service...")

# Initialize FastAPI App
app = FastAPI(
    title="DocMind API",
    description="A modular, production-ready full-stack backend serving PDF citations and LLM chat requests.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS Middleware
setup_cors(app)

# Register Sub-Routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)

@app.get("/health")
def health_check():
    """Simple service health endpoint for Render or monitoring services."""
    return {"status": "healthy", "service": "DocMind Backend"}

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)
