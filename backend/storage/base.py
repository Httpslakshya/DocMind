from abc import ABC, abstractmethod
from typing import BinaryIO

class BaseStorage(ABC):
    """Abstract interface defining required storage provider behavior."""

    @abstractmethod
    def save_file(self, filename: str, file_obj: BinaryIO) -> str:
        """
        Saves a binary file to the storage backend.
        
        Args:
            filename: Name of the file.
            file_obj: Binary file stream wrapper.
            
        Returns:
            The path, key, or reference string of the stored file.
        """
        pass
        
    @abstractmethod
    def get_file_path(self, filename: str) -> str:
        """
        Returns a path reference to serve the file.
        
        Args:
            filename: Name of the target file.
            
        Returns:
            An absolute string path or public URL.
        """
        pass
        
    @abstractmethod
    def delete_file(self, filename: str) -> bool:
        """
        Deletes the target file.
        
        Args:
            filename: Name of the file to delete.
            
        Returns:
            bool: True if deletion was successful, False otherwise.
        """
        pass
        
    @abstractmethod
    def exists(self, filename: str) -> bool:
        """
        Checks if a file exists in the storage backend.
        
        Args:
            filename: Name of the file.
            
        Returns:
            bool: True if file exists, False otherwise.
        """
        pass

    @abstractmethod
    def get_file_url(self, filename: str) -> str:
        """
        Returns a public or signed URL to access the file directly.
        
        Args:
            filename: Name of the file.
            
        Returns:
            str: Public URL or signed download link.
        """
        pass
