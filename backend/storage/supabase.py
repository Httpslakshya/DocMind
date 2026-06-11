import os
import shutil
from typing import BinaryIO
from supabase import create_client, Client
from backend.storage.base import BaseStorage
from backend.config.settings import settings
from backend.utils.logging_config import logger

class SupabaseStorage(BaseStorage):
    """Production cloud file storage provider powered by Supabase Storage."""

    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
        self.bucket = settings.SUPABASE_BUCKET
        self.cache_dir = settings.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        if not self.url or not self.key:
            logger.error("SupabaseStorage initialized with missing credentials!")
            raise ValueError("Supabase integration requires SUPABASE_URL and SUPABASE_KEY variables.")
            
        logger.info(f"Initializing Supabase Storage Client (Bucket: '{self.bucket}').")
        self.client: Client = create_client(self.url, self.key)

    def save_file(self, filename: str, file_obj: BinaryIO) -> str:
        """Caches file locally, then uploads it to Supabase Storage."""
        cache_path = self.cache_dir / filename
        try:
            # 1. Save locally in Cache for immediate fast access / indexing
            with open(cache_path, "wb") as buffer:
                shutil.copyfileobj(file_obj, buffer)
            logger.info(f"Cached file '{filename}' locally at {cache_path}.")
            
            # 2. Upload to Supabase Storage (setting upsert=True)
            with open(cache_path, "rb") as f:
                self.client.storage.from_(self.bucket).upload(
                    path=filename,
                    file=f,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
            logger.info(f"Successfully uploaded file '{filename}' to Supabase Storage.")
            return str(cache_path)
        except Exception as e:
            logger.error(f"Failed to upload '{filename}' to Supabase bucket: {e}", exc_info=True)
            if cache_path.exists():
                cache_path.unlink()
            raise IOError(f"Supabase Storage Upload failed: {e}")

    def get_file_path(self, filename: str) -> str:
        """Returns the local cache file path. Downloads from Supabase first if cache is cold."""
        cache_path = self.cache_dir / filename
        
        # Pull down from cloud if cache is missing
        if not cache_path.exists():
            logger.info(f"Cache miss for '{filename}'. Downloading file from Supabase Storage...")
            try:
                response = self.client.storage.from_(self.bucket).download(filename)
                with open(cache_path, "wb") as f:
                    f.write(response)
                logger.info(f"Cached file '{filename}' successfully from Supabase Storage.")
            except Exception as e:
                logger.error(f"Failed to download '{filename}' from Supabase Storage: {e}", exc_info=True)
                raise FileNotFoundError(f"Cloud file '{filename}' could not be downloaded: {e}")
                
        return str(cache_path)

    def delete_file(self, filename: str) -> bool:
        """Cleans up local cache file and deletes target from Supabase Storage."""
        cache_path = self.cache_dir / filename
        deleted = True
        
        if cache_path.exists():
            try:
                cache_path.unlink()
                logger.info(f"Deleted local cache copy for '{filename}'.")
            except Exception as e:
                logger.error(f"Failed to delete local cache file '{filename}': {e}")
                deleted = False
                
        try:
            self.client.storage.from_(self.bucket).remove([filename])
            logger.info(f"Successfully deleted '{filename}' from Supabase Storage.")
        except Exception as e:
            logger.error(f"Failed to delete '{filename}' from Supabase Storage bucket: {e}", exc_info=True)
            deleted = False
            
        return deleted

    def exists(self, filename: str) -> bool:
        """Returns True if file exists in either local cache or Supabase Storage."""
        cache_path = self.cache_dir / filename
        if cache_path.exists():
            return True
            
        try:
            # Look up file in Supabase catalog
            files = self.client.storage.from_(self.bucket).list(
                path="",
                options={"limit": 1, "search": filename}
            )
            for f in files:
                if f.get("name") == filename:
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to check file existence in Supabase: {e}")
            return False

    def get_file_url(self, filename: str) -> str:
        """Generates a retrieval URL for this file (public by default, signed link fallback)."""
        try:
            public_url = self.client.storage.from_(self.bucket).get_public_url(filename)
            return public_url
        except Exception as e:
            logger.warning(f"Could not generate public URL for '{filename}': {e}. Falling back to signed URL...")
            try:
                # Falls back to authenticated signed link (valid for 1 hour)
                res = self.client.storage.from_(self.bucket).create_signed_url(filename, 3600)
                return res.get("signedURL", "")
            except Exception as se:
                logger.error(f"Failed to generate signed URL for '{filename}': {se}", exc_info=True)
                return ""
