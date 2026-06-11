import re
from fastapi import UploadFile, HTTPException
from backend.config.settings import settings
from backend.utils.logging_config import logger

def sanitize_filename(filename: str) -> str:
    """Sanitizes filename to prevent directory traversal and strip unsafe characters."""
    # Split filename and extension
    name_parts = filename.rsplit('.', 1)
    name = name_parts[0]
    ext = name_parts[1] if len(name_parts) > 1 else 'pdf'
    
    # Replace anything that isn't alphanumeric, dash, or underscore with underscore
    clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    
    # Trim to reasonable length and rejoin
    return f"{clean_name[:100]}.{ext}"

def format_size(bytes_size: int) -> str:
    """Formats bytes into human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def validate_uploaded_file(file: UploadFile):
    """Performs safety checks including PDF extension, content type, and file size limits."""
    # 1. Check extension
    if not file.filename.lower().endswith('.pdf'):
        logger.warning(f"File upload rejected: {file.filename} lacks .pdf extension.")
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    # 2. Check content-type / MIME type
    if file.content_type and file.content_type != "application/pdf":
        logger.warning(f"File upload rejected: {file.filename} reports content-type {file.content_type}.")
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")
        
    # 3. Check file size limits
    # We can check size by seeking if needed, or by reading chunk size
    # FastAPI UploadFile keeps files in memory (if <1MB) or SpooledTemporaryFile on disk.
    # To check the file size without loading everything into memory at once:
    try:
        file.file.seek(0, 2)
        size_bytes = file.file.tell()
        file.file.seek(0)  # Reset pointer to start
    except Exception as e:
        logger.error(f"Error checking file size for {file.filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal file processing error")
        
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        logger.warning(f"File upload rejected: {file.filename} is {format_size(size_bytes)}, exceeding limit of {settings.MAX_FILE_SIZE_MB}MB.")
        raise HTTPException(
            status_code=400, 
            detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
        )
        
    return size_bytes
