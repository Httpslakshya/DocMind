import os
import shutil
from typing import BinaryIO
from backend.storage.base import BaseStorage
from backend.config.settings import settings
from backend.utils.logging_config import logger

class LocalStorage(BaseStorage):
    """Local disk filesystem implementation of the storage interface."""

    def __init__(self, data_dir=None):
        self.data_dir = data_dir or settings.DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
        
    def save_file(self, filename: str, file_obj: BinaryIO) -> str:
        file_path = os.path.join(self.data_dir, filename)
        try:
            # Copy input buffer to target file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file_obj, buffer)
            logger.info(f"Successfully saved {filename} to local data directory.")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save file {filename} locally: {e}")
            raise IOError(f"Failed to save file: {e}")
            
    def get_file_path(self, filename: str) -> str:
        file_path = os.path.join(self.data_dir, filename)
        return file_path
        
    def delete_file(self, filename: str) -> bool:
        file_path = os.path.join(self.data_dir, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Successfully deleted {filename} from local directory.")
                return True
            except Exception as e:
                logger.error(f"Failed to remove file {filename} from local directory: {e}")
                return False
        logger.warning(f"Delete requested for missing local file: {filename}")
        return False
        
    def exists(self, filename: str) -> bool:
        file_path = os.path.join(self.data_dir, filename)
        return os.path.exists(file_path)

    def get_file_url(self, filename: str) -> str:
        """For local storage, returns the local API path relative to the host."""
        return f"/api/document/{filename}"
