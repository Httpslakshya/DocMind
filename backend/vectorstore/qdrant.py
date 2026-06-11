from backend.config.settings import settings
from backend.utils.logging_config import logger

_qdrant_client = None
_vector_db = None
_embeddings = None

def get_embeddings():
    """Initializes and caches the Hugging Face sentence embeddings model."""
    global _embeddings
    if _embeddings is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        logger.info("Loading sentence-transformers/all-MiniLM-L6-v2 embedding model...")
        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embeddings

def get_qdrant_client():
    """Returns a cached QdrantClient configured for remote Cloud or local fallback."""
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient

        qdrant_url = settings.QDRANT_URL
        qdrant_api_key = settings.QDRANT_API_KEY
        
        # Connect to remote Qdrant Cloud if configuration exists
        if qdrant_url and "localhost" not in qdrant_url:
            logger.info(f"Connecting to remote Qdrant Cloud instance: {qdrant_url}")
            _qdrant_client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                prefer_grpc=False
            )
        else:
            local_path = str(settings.QDRANT_LOCAL_PATH)
            logger.info(f"Remote Qdrant details missing or pointing to localhost. Connecting to local Qdrant DB at {local_path}...")
            _qdrant_client = QdrantClient(path=local_path)
            
    return _qdrant_client

def get_vector_db():
    """Returns the LangChain QdrantVectorStore wrapper instance."""
    global _vector_db
    if _vector_db is None:
        from langchain_qdrant import QdrantVectorStore

        client = get_qdrant_client()
        embeddings = get_embeddings()
        logger.info("Initializing LangChain QdrantVectorStore wrapper (collection: 'chatpdf')...")
        _vector_db = QdrantVectorStore(
            client=client,
            embedding=embeddings,
            collection_name="chatpdf"
        )
    return _vector_db
