from backend.config.settings import settings
from backend.vectorstore.qdrant import get_vector_db, get_qdrant_client
from backend.utils.logging_config import logger

def index_document(filename: str, file_path: str) -> int:
    """
    Loads, splits, and embeds a PDF file into Qdrant.
    
    Returns:
        int: Number of pages indexed.
    """
    logger.info(f"Indexing process started for file: {filename}")
    try:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        loader = PyPDFLoader(file_path)
        docs = loader.load()
        page_count = len(docs)
        logger.info(f"Successfully loaded {page_count} pages from {filename}.")
        
        # Split documents into overlapping chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=400
        )
        chunks = text_splitter.split_documents(docs)
        
        # Set normalized metadata
        for chunk in chunks:
            chunk.metadata["source"] = filename
            if "page" in chunk.metadata:
                chunk.metadata["page_label"] = str(chunk.metadata["page"] + 1)
            else:
                chunk.metadata["page_label"] = "1"
                
        # Index in Qdrant
        vector_db = get_vector_db()
        vector_db.add_documents(chunks)
        logger.info(f"Added {len(chunks)} chunks to Qdrant collection for '{filename}'.")
        return page_count
        
    except Exception as e:
        logger.error(f"Error during indexing of document {filename}: {e}", exc_info=True)
        raise RuntimeError(f"Failed to process and index PDF: {e}")

def delete_document_vectors(filename: str):
    """Deletes all vectorized points associated with the filename source."""
    logger.info(f"Deleting vector points in Qdrant for document: {filename}")
    try:
        from qdrant_client.http import models as rest

        client = get_qdrant_client()
        client.delete(
            collection_name="chatpdf",
            points_selector=rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="metadata.source",
                        match=rest.MatchValue(value=filename)
                    )
                ]
            )
        )
        logger.info(f"Successfully deleted vectors for document: {filename}")
    except Exception as e:
        logger.error(f"Failed to delete Qdrant points for {filename}: {e}", exc_info=True)

def call_llm(system_prompt: str, user_query: str) -> str:
    """Routes completion request to Groq API with automatic fallback to Gemini."""
    # 1. Attempt Groq call
    groq_api_key = settings.GROQ_API_KEY
    if groq_api_key:
        try:
            logger.info("Executing completion request to Groq API...")
            from openai import OpenAI
            client = OpenAI(
                api_key=groq_api_key,
                base_url="https://api.groq.com/openai/v1"
            )
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}. Attempting fallback to Gemini API...")
            
    # 2. Fallback to Gemini
    gemini_api_key = settings.GEMINI_API_KEY
    if gemini_api_key:
        try:
            logger.info("Executing completion request to Gemini API (fallback)...")
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config={"temperature": 0.2}
            )
            full_prompt = f"{system_prompt}\n\nUser Question:\n{user_query}"
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API fallback call failed: {e}", exc_info=True)
            
    return "Error: Unable to connect to LLM APIs (Both Groq and Gemini calls failed or are unconfigured)."
