import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from backend.config.settings import settings
from backend.storage.service import storage_service
from backend.utils.helpers import sanitize_filename, format_size, validate_uploaded_file
from backend.models.schemas import success_response, error_response
from backend.utils.logging_config import logger

router = APIRouter(tags=["Documents"])

# ---------------------------------------------------------------------------
# Supabase job status helpers (restart-proof — no more in-memory dict)
# ---------------------------------------------------------------------------

def _get_supabase():
    """Returns a Supabase client instance."""
    from supabase import create_client
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def _job_create(job_id: str, filename: str):
    """Inserts a new indexing job record into Supabase."""
    try:
        _get_supabase().table("indexing_jobs").insert({
            "job_id": job_id,
            "filename": filename,
            "status": "queued",
            "progress": 0,
            "pages": 0,
            "error": None
        }).execute()
    except Exception as e:
        logger.warning(f"Could not persist job {job_id} to Supabase: {e}")

def _job_update(job_id: str, **kwargs):
    """Updates fields on an existing indexing job record in Supabase."""
    try:
        _get_supabase().table("indexing_jobs").update(kwargs).eq("job_id", job_id).execute()
    except Exception as e:
        logger.warning(f"Could not update job {job_id} in Supabase: {e}")

def _job_get(job_id: str):
    """Fetches a single indexing job record from Supabase. Returns dict or None."""
    try:
        result = _get_supabase().table("indexing_jobs").select("*").eq("job_id", job_id).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        logger.warning(f"Could not fetch job {job_id} from Supabase: {e}")
    return None

# ---------------------------------------------------------------------------
# Local JSON document catalog helpers
# ---------------------------------------------------------------------------

def load_documents_db():
    """Reads document metadata tracking list from local json database."""
    try:
        if not settings.DOCS_DB_PATH.exists():
            with open(settings.DOCS_DB_PATH, "w", encoding="utf-8") as f:
                json.dump([], f)
            return []
        with open(settings.DOCS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read documents DB: {e}")
        return []

def save_documents_db(db):
    """Writes document metadata tracking list to local json database."""
    try:
        with open(settings.DOCS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to write documents DB: {e}")

# ---------------------------------------------------------------------------
# Background indexing worker
# ---------------------------------------------------------------------------

async def bg_index_document(job_id: str, filename: str, file_path: str):
    """Background task to load, chunk, embed, and index a PDF document."""
    logger.info(f"Background indexing worker started for job {job_id} ({filename})")
    try:
        # Step 1: Ingestion
        _job_update(job_id, status="processing", progress=15)

        from langchain_community.document_loaders import PyPDFLoader
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        page_count = len(docs)
        logger.info(f"Loaded {page_count} pages for job {job_id}.")

        # Step 2: Chunking
        _job_update(job_id, progress=45)
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=400)
        chunks = text_splitter.split_documents(docs)

        for chunk in chunks:
            chunk.metadata["source"] = filename
            chunk.metadata["page_label"] = str(chunk.metadata.get("page", 0) + 1)

        # Step 3: Embed + index into Qdrant
        _job_update(job_id, progress=70)
        from backend.vectorstore.qdrant import get_vector_db
        vector_db = get_vector_db()
        vector_db.add_documents(chunks)

        # Step 4: Persist metadata catalog
        _job_update(job_id, progress=90)
        db = load_documents_db()
        file_size_formatted = format_size(os.path.getsize(file_path))
        storage_url = storage_service.get_file_url(filename)

        exists = False
        for doc in db:
            if doc["filename"] == filename:
                doc["size"] = file_size_formatted
                doc["pages"] = page_count
                doc["date"] = datetime.now().strftime("%b %d, %Y")
                doc["indexed"] = True
                doc["last_activity"] = datetime.now().strftime("%b %d, %Y %I:%M %p")
                doc["storage_url"] = storage_url
                exists = True
                break

        if not exists:
            db.append({
                "filename": filename,
                "size": file_size_formatted,
                "pages": page_count,
                "date": datetime.now().strftime("%b %d, %Y"),
                "chats": 0,
                "indexed": True,
                "last_activity": datetime.now().strftime("%b %d, %Y %I:%M %p"),
                "storage_url": storage_url,
                "summary": "Ready for analysis. Ask DocMind to summarize, quiz, or extract the core concepts."
            })
        save_documents_db(db)

        # Step 5: Mark completed
        _job_update(job_id, status="completed", progress=100, pages=page_count)
        logger.info(f"Indexing completed for job {job_id} ({filename})")

    except Exception as e:
        logger.error(f"Background indexing failed for job {job_id} ({filename}): {e}", exc_info=True)
        _job_update(job_id, status="failed", progress=0, error=str(e))

        try:
            storage_service.delete_file(filename)
        except Exception as cleanup_err:
            logger.warning(f"Cleanup failed for {filename}: {cleanup_err}")

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/api/documents")
def get_documents():
    """Retrieves document library catalog and validates physical file presence."""
    db = load_documents_db()
    synced_db = []
    changed = False

    for doc in db:
        if storage_service.exists(doc["filename"]):
            synced_db.append(doc)
        else:
            changed = True
            logger.info(f"Removing reference for physically missing file: {doc['filename']}")

    if changed:
        save_documents_db(synced_db)

    return success_response(
        data={"documents": synced_db},
        message="Documents retrieved successfully"
    )

@router.get("/api/document/meta/{filename}")
def get_document_meta(filename: str):
    """Retrieves metadata properties for a given file name."""
    sanitized = sanitize_filename(filename)
    db = load_documents_db()

    for doc in db:
        if doc["filename"] == sanitized:
            if not storage_service.exists(sanitized):
                return error_response(message="Document not found on storage backend", status_code=404)

            file_path = storage_service.get_file_path(sanitized)
            file_size_formatted = doc.get("size", format_size(os.path.getsize(file_path)))

            return success_response(
                data={
                    "filename": doc["filename"],
                    "size": file_size_formatted,
                    "pages": doc.get("pages", 0),
                    "date": doc.get("date", "Unknown"),
                    "chats": doc.get("chats", 0),
                    "indexed": doc.get("pages", 0) > 0,
                    "last_activity": doc.get("last_activity", doc.get("date", "Unknown")),
                    "storage_url": doc.get("storage_url", storage_service.get_file_url(sanitized)),
                    "summary": doc.get(
                        "summary",
                        "No saved summary yet. Use Generate Notes, Generate Quiz, or Summarize Document to create a focused readout."
                    ),
                },
                message="Metadata retrieved successfully"
            )

    return error_response(message="Document metadata reference not found", status_code=404)

@router.get("/api/document/{filename}")
def serve_document(filename: str):
    """Serves the binary PDF content for in-browser rendering."""
    sanitized = sanitize_filename(filename)
    if not storage_service.exists(sanitized):
        return error_response(message="Document not found", status_code=404)

    file_path = storage_service.get_file_path(sanitized)
    return FileResponse(file_path, media_type="application/pdf")

@router.delete("/api/document/{filename}")
def delete_document(filename: str):
    """Deletes document from storage, metadata catalog, and Qdrant vectors."""
    sanitized = sanitize_filename(filename)

    storage_service.delete_file(sanitized)

    db = load_documents_db()
    new_db = [doc for doc in db if doc["filename"] != sanitized]
    save_documents_db(new_db)

    from backend.services.rag import delete_document_vectors
    delete_document_vectors(sanitized)

    logger.info(f"Completed deletion tasks for {sanitized}.")
    return success_response(message=f"Document {sanitized} deleted successfully")

@router.get("/api/document/status/{filename}")
def get_document_status(filename: str, background_tasks: BackgroundTasks):
    """Polls/Checks if document requires RAG indexing and triggers it if pending."""
    sanitized = sanitize_filename(filename)
    db = load_documents_db()

    for doc in db:
        if doc["filename"] == sanitized:
            if doc.get("pages", 0) == 0:
                try:
                    if not storage_service.exists(sanitized):
                        return error_response(message="Seeded file reference lost on storage", status_code=404)

                    file_path = storage_service.get_file_path(sanitized)
                    job_id = f"auto-{str(uuid.uuid4())[:8]}"
                    _job_create(job_id, sanitized)
                    background_tasks.add_task(bg_index_document, job_id, sanitized, file_path)

                    return success_response(
                        data={"status": "processing", "job_id": job_id},
                        message="Indexing triggered in background"
                    )
                except Exception as e:
                    logger.error(f"Auto-indexing dispatch failed for {sanitized}: {e}")
                    return success_response(
                        data={"status": "error", "detail": str(e)},
                        message="Indexing dispatch failed"
                    )
            else:
                return success_response(
                    data={"status": "indexed", "pages": doc["pages"]},
                    message="Document is indexed"
                )

    return success_response(
        data={"status": "not_found"},
        message="Document status query finished: record not found"
    )

@router.post("/api/upload")
def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Receives PDF, saves to storage, and queues RAG indexing in background."""
    sanitized = sanitize_filename(file.filename)
    logger.info(f"File upload request received for background indexing: {file.filename}")

    validate_uploaded_file(file)

    file_path = storage_service.save_file(sanitized, file.file)

    job_id = str(uuid.uuid4())
    _job_create(job_id, sanitized)
    background_tasks.add_task(bg_index_document, job_id, sanitized, file_path)

    logger.info(f"Queued background indexing job {job_id} for file '{sanitized}'.")

    return success_response(
        data={
            "job_id": job_id,
            "filename": sanitized,
            "status": "queued"
        },
        message="Upload completed. Document is queued for indexing."
    )

@router.get("/api/upload/status/{job_id}")
def get_upload_status(job_id: str):
    """Retrieves status and progress for a background indexing job from Supabase."""
    job = _job_get(job_id)
    if not job:
        return error_response(message="Background indexing job not found", status_code=404)

    return success_response(
        data=job,
        message="Background job status retrieved successfully"
    )

def seed_documents():
    """Copies seeded documents from agentic resources if database catalog is empty."""
    if settings.STORAGE_PROVIDER.lower() != "local" and os.getenv("SEED_ON_STARTUP", "false").lower() != "true":
        logger.info("Skipping startup document seeding for non-local storage provider.")
        return

    rag_dir = Path(r"d:\Codes\anaconda\Agentic_Ai\RAG")
    if not rag_dir.exists():
        logger.info("Seed directory 'Agentic_Ai/RAG' does not exist. Skipping seeding.")
        return

    db = load_documents_db()
    if len(db) > 0:
        return

    seeded = False
    for item in os.listdir(rag_dir):
        if item.endswith(".pdf"):
            src_path = rag_dir / item
            sanitized = sanitize_filename(item)

            try:
                with open(src_path, "rb") as f:
                    storage_service.save_file(sanitized, f)

                file_path = storage_service.get_file_path(sanitized)
                file_size_formatted = format_size(os.path.getsize(file_path))

                db.append({
                    "filename": sanitized,
                    "size": file_size_formatted,
                    "pages": 0,
                    "date": datetime.now().strftime("%b %d, %Y"),
                    "chats": 0,
                    "indexed": False,
                    "storage_url": storage_service.get_file_url(sanitized)
                })
                seeded = True
                logger.info(f"Successfully seeded document: {sanitized}")
            except Exception as e:
                logger.error(f"Failed to seed document {item}: {e}")

    if seeded:
        save_documents_db(db)