from backend.config.settings import settings
from backend.storage.local import LocalStorage
from backend.utils.logging_config import logger

_storage_service = None

def get_storage_service():
    """Factory function to retrieve the configured storage provider."""
    global _storage_service
    if _storage_service is not None:
        return _storage_service

    provider = settings.STORAGE_PROVIDER.lower()
    
    if provider == "supabase":
        logger.info("Instantiating SupabaseStorage provider.")
        from backend.storage.supabase import SupabaseStorage
        _storage_service = SupabaseStorage()
    elif provider == "local":
        logger.info("Instantiating LocalStorage provider.")
        _storage_service = LocalStorage()
    else:
        logger.warning(f"Unknown storage provider '{provider}'. Falling back to LocalStorage.")
        _storage_service = LocalStorage()
    return _storage_service

class LazyStorageService:
    """Defers storage provider construction until an endpoint actually needs it."""

    def __getattr__(self, name):
        return getattr(get_storage_service(), name)

storage_service = LazyStorageService()
