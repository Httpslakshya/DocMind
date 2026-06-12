from backend.config.settings import settings
from backend.utils.logging_config import logger

_qdrant_client = None
_vector_db = None
_embeddings = None

def get_embeddings():
    """Initializes and caches Google Gemini text-embedding-004 model."""
    global _embeddings
    if _embeddings is None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        logger.info("Initializing Google Gemini gemini-embedding-001 model (768 dim)...")
        _embeddings = GoogleGenerativeAIEmbeddings(
            model="gemini-embedding-001",
            google_api_key=settings.GEMINI_API_KEY
        )
        logger.info("Google Gemini embeddings initialized successfully.")
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
            logger.info(f"Connecting to local Qdrant DB at {local_path}...")
            _qdrant_client = QdrantClient(path=local_path)

    return _qdrant_client

def ensure_collection_exists():
    """Creates 'chatpdf' collection with 768 dimensions if it doesn't exist."""
    from qdrant_client.models import Distance, VectorParams
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]
    if "chatpdf" not in existing:
        logger.info("Collection 'chatpdf' not found. Creating with 768 dimensions (Gemini)...")
        client.create_collection(
            collection_name="chatpdf",
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
        logger.info("Collection 'chatpdf' created successfully.")
    else:
        logger.info("Collection 'chatpdf' already exists.")

def get_vector_db():
    """Returns the LangChain QdrantVectorStore wrapper instance."""
    global _vector_db
    if _vector_db is None:
        from langchain_qdrant import QdrantVectorStore

        ensure_collection_exists()
        client = get_qdrant_client()
        embeddings = get_embeddings()
        logger.info("Initializing LangChain QdrantVectorStore wrapper (collection: 'chatpdf')...")
        _vector_db = QdrantVectorStore(
            client=client,
            embedding=embeddings,
            collection_name="chatpdf"
        )
        logger.info("QdrantVectorStore initialized successfully.")
    return _vector_db