from datetime import datetime
from fastapi import APIRouter
from backend.models.schemas import ChatRequest, success_response, error_response
from backend.api.documents import load_documents_db, save_documents_db
from backend.storage.service import storage_service
from backend.utils.logging_config import logger

router = APIRouter(tags=["Chat"])

@router.post("/api/chat")
def api_chat(chat_req: ChatRequest):
    """Retrieves document chunks matching queries from Qdrant, prompts the LLM, and logs analytics."""
    filename = chat_req.filename
    user_query = chat_req.message
    
    logger.info(f"Received query for document '{filename}': {user_query[:50]}...")
    
    # Validate file presence
    if not storage_service.exists(filename):
        logger.warning(f"RAG Chat failed: file '{filename}' does not exist on storage backend.")
        return error_response("Active document not found in file storage", status_code=404)
        
    try:
        from qdrant_client.http import models as rest
        from backend.vectorstore.qdrant import get_vector_db
        from backend.services.rag import call_llm

        vector_db = get_vector_db()
        
        # Apply metadata filter to lock results to this specific document
        search_results = vector_db.similarity_search(
            query=user_query,
            k=4,
            filter=rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="metadata.source",
                        match=rest.MatchValue(value=filename)
                    )
                ]
            )
        )
        
        # Format the context block
        context_parts = []
        sources = []
        for doc in search_results:
            page_num = doc.metadata.get("page_label", "Unknown")
            context_parts.append(f"Page Content: {doc.page_content}\nPage Number: {page_num}\nFile: {filename}")
            sources.append(page_num)
            
        context = "\n\n---\n\n".join(context_parts)
        
        # Filter and sort page sources numerically
        unique_sources = sorted(list(set(sources)), key=lambda x: int(x) if x.isdigit() else 999)
        
        system_prompt = f"""You are a helpful AI Assistant who answers user queries based on the available context retrieved from a PDF file.

You must only answer the user based on the following context. If the query cannot be answered using the context, state that you do not have sufficient information.
Navigate the user to open the right page numbers to know more.

Context:
{context}
"""
        # Call LLM orchestrator
        llm_response = call_llm(system_prompt, user_query)
        
        # Increment chat count and activity date in metadata database
        db = load_documents_db()
        for doc in db:
            if doc["filename"] == filename:
                doc["chats"] = doc.get("chats", 0) + 1
                doc["last_activity"] = datetime.now().strftime("%b %d, %Y %I:%M %p")
                break
        save_documents_db(db)
        
        logger.info(f"RAG query finished successfully for '{filename}'. Sources: {unique_sources}")
        return success_response(
            data={
                "answer": llm_response,
                "sources": unique_sources
            },
            message="Chat response completed successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to execute RAG query for '{filename}': {e}", exc_info=True)
        return error_response(message=f"RAG engine query error: {str(e)}", status_code=500)
