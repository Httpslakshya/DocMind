import os
import json
import shutil
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dotenv import load_dotenv
# Load environment variables
load_dotenv()

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DOCS_DB_PATH = os.path.join(BASE_DIR, "documents.json")
QDRANT_LOCAL_PATH = os.path.join(BASE_DIR, "qdrant_db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Initialize document tracking DB
if not os.path.exists(DOCS_DB_PATH):
    with open(DOCS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump([], f)

app = FastAPI(
    title="DocMind Backend",
    description="A Neubrutalist PDF chat application powered by RAG.",
)

# Lazy imports/initializers for langchain/qdrant to ensure startup doesn't fail if dependencies are still loading
_embedding_model = None
_qdrant_client = None
_vector_db = None

def get_embeddings():
    global _embedding_model
    if _embedding_model is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        _embedding_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
    return _embedding_model

def get_qdrant_client():
    global _qdrant_client
    if _qdrant_client is None:
        from qdrant_client import QdrantClient
        
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")
        
        # Check if remote Qdrant is available, otherwise fallback to local disk DB
        if qdrant_url and "localhost" not in qdrant_url:
            print(f"Connecting to remote Qdrant at {qdrant_url}...")
            _qdrant_client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                prefer_grpc=False
            )
        else:
            print(f"Connecting to local Qdrant at {QDRANT_LOCAL_PATH}...")
            _qdrant_client = QdrantClient(path=QDRANT_LOCAL_PATH)
    return _qdrant_client

def get_vector_db():
    global _vector_db
    if _vector_db is None:
        from langchain_qdrant import QdrantVectorStore
       
        _vector_db = QdrantVectorStore(
            client=get_qdrant_client(),
            embedding=get_embeddings(),
            collection_name="chatpdf"
        )
    return _vector_db

# Mock Auth state
# Simple server-side session tracking using cookies or memory for this demonstration
active_sessions = set()

def load_documents_db():
    try:
        with open(DOCS_DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_documents_db(db):
    with open(DOCS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)

def format_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

# Root redirects to login or dashboard
@app.get("/")
def read_root(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in active_sessions:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
def get_login_page():
    return FileResponse(os.path.join(STATIC_DIR, "login.html"))

@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard_page(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id not in active_sessions:
         return RedirectResponse(url="/login")
    return FileResponse(os.path.join(STATIC_DIR, "dashboard.html"))

@app.get("/processing", response_class=HTMLResponse)
def get_processing_page(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id not in active_sessions:
         return RedirectResponse(url="/login")
    return FileResponse(os.path.join(STATIC_DIR, "processing.html"))

@app.get("/chat", response_class=HTMLResponse)
def get_chat_page(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id not in active_sessions:
         return RedirectResponse(url="/login")
    return FileResponse(os.path.join(STATIC_DIR, "chat.html"))

@app.get("/document", response_class=HTMLResponse)
def get_document_details_page(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id not in active_sessions:
         return RedirectResponse(url="/login")
    return FileResponse(os.path.join(STATIC_DIR, "document.html"))

# API Auth endpoint
@app.post("/api/login")
def api_login(email: str = Form(...), password: str = Form(...)):
    # Simple demo auth: accepts any credentials to make it easy to run
    session_id = email
    active_sessions.add(session_id)
    response = JSONResponse(content={"status": "success", "redirect": "/dashboard"})
    response.set_cookie(key="session_id", value=session_id)
    return response

@app.post("/api/logout")
def api_logout(request: Request):
    session_id = request.cookies.get("session_id")
    if session_id in active_sessions:
        active_sessions.remove(session_id)
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="session_id")
    return response

# Get all tracked documents
@app.get("/api/documents")
def get_documents():
    db = load_documents_db()
    # Ensure physical files exist, else sync DB
    synced_db = []
    changed = False
    for doc in db:
        if os.path.exists(os.path.join(DATA_DIR, doc["filename"])):
            synced_db.append(doc)
        else:
            changed = True
    if changed:
        save_documents_db(synced_db)
    return synced_db

@app.get("/api/document/meta/{filename}")
def get_document_meta(filename: str):
    db = load_documents_db()
    for doc in db:
        if doc["filename"] == filename:
            file_path = os.path.join(DATA_DIR, filename)
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="Document not found")

            return {
                "filename": doc["filename"],
                "size": doc.get("size", format_size(os.path.getsize(file_path))),
                "pages": doc.get("pages", 0),
                "date": doc.get("date", "Unknown"),
                "chats": doc.get("chats", 0),
                "indexed": doc.get("pages", 0) > 0,
                "last_activity": doc.get("last_activity", doc.get("date", "Unknown")),
                "summary": doc.get(
                    "summary",
                    "No saved summary yet. Use Generate Notes, Generate Quiz, or Summarize Document to create a focused readout.",
                ),
            }
    raise HTTPException(status_code=404, detail="Document not found")

# Serve uploaded document files
@app.get("/api/document/{filename}")
def serve_document(filename: str):
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(file_path)

# Delete document and its local files
@app.delete("/api/document/{filename}")
def delete_document(filename: str):
    file_path = os.path.join(DATA_DIR, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        
    db = load_documents_db()
    new_db = [doc for doc in db if doc["filename"] != filename]
    save_documents_db(new_db)
    
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
    except Exception as e:
        print(f"Failed to delete Qdrant points for {filename}: {e}")
        
    return {"status": "success", "detail": f"Document {filename} deleted"}

# Get document indexing status and auto-index if needed
@app.get("/api/document/status/{filename}")
def get_document_status(filename: str):
    db = load_documents_db()
    for doc in db:
        if doc["filename"] == filename:
            if doc.get("pages", 0) == 0:
                try:
                    file_path = os.path.join(DATA_DIR, filename)
                    if not os.path.exists(file_path):
                        raise HTTPException(status_code=404, detail="Seeded file not found on disk")
                        
                    from langchain_community.document_loaders import PyPDFLoader
                    from langchain_text_splitters import RecursiveCharacterTextSplitter
                    
                    print(f"Auto-indexing seeded file: {filename}...")
                    loader = PyPDFLoader(file_path)
                    docs = loader.load()
                    page_count = len(docs)
                    
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=400)
                    chunks = text_splitter.split_documents(docs)
                    
                    for chunk in chunks:
                        chunk.metadata["source"] = filename
                        if "page" in chunk.metadata:
                            chunk.metadata["page_label"] = str(chunk.metadata["page"] + 1)
                        else:
                            chunk.metadata["page_label"] = "1"
                            
                    vector_db = get_vector_db()
                    vector_db.add_documents(chunks)
                    
                    doc["pages"] = page_count
                    save_documents_db(db)
                    print(f"Auto-indexing of {filename} complete: {page_count} pages.")
                    return {"status": "indexed", "pages": page_count}
                except Exception as e:
                    print(f"Failed to auto-index {filename}: {e}")
                    return {"status": "error", "detail": str(e)}
            else:
                return {"status": "indexed", "pages": doc["pages"]}
    return {"status": "not_found"}

# Upload PDF and index it in background or synchronously
@app.post("/api/upload")
def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    filename = file.filename
    file_path = os.path.join(DATA_DIR, filename)
    
    # Save the file locally
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    file_size_bytes = os.path.getsize(file_path)
    file_size_formatted = format_size(file_size_bytes)
    
    # Process the PDF document for RAG indexing
    try:
        from langchain_community.document_loaders import PyPDFLoader
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        # Load PDF
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        page_count = len(docs)
        
        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=400
        )
        chunks = text_splitter.split_documents(docs)
        
        # Override metadata source to be just the filename (not absolute path) so we can query filter it easily
        for chunk in chunks:
            chunk.metadata["source"] = filename
            # PyPDFLoader extracts page number into 'page', let's ensure 'page_label' exists
            if "page" in chunk.metadata:
                chunk.metadata["page_label"] = str(chunk.metadata["page"] + 1)
            else:
                chunk.metadata["page_label"] = "1"
        
        # Index in Qdrant Vector Store
        vector_db = get_vector_db()
        vector_db.add_documents(chunks)
        
        # Save tracking meta to documents.json
        db = load_documents_db()
        # Check if already exists, update size and page count
        exists = False
        for doc in db:
            if doc["filename"] == filename:
                doc["size"] = file_size_formatted
                doc["pages"] = page_count
                doc["date"] = datetime.now().strftime("%b %d, %Y")
                doc["indexed"] = True
                doc["last_activity"] = datetime.now().strftime("%b %d, %Y %I:%M %p")
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
                "summary": "Ready for analysis. Ask DocMind to summarize, quiz, or extract the core concepts."
            })
        save_documents_db(db)
        
        return {"status": "success", "filename": filename, "pages": page_count}
    except Exception as e:
        print(f"Error indexing PDF {filename}: {e}")
        # Clean up if failed
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to process and index PDF: {str(e)}")

# RAG Chat Request Schema
class ChatRequest(BaseModel):
    filename: str
    message: str

# RAG Chat Endpoint
@app.post("/api/chat")
def api_chat(chat_req: ChatRequest):
    filename = chat_req.filename
    user_query = chat_req.message
    
    file_path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Currently active document not found in files")
        
    try:
        from qdrant_client.http import models as rest
        vector_db = get_vector_db()
        
        # Filter similarity search to only search this specific document
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
        
        # Construct Context
        context_parts = []
        sources = []
        for doc in search_results:
            page_num = doc.metadata.get("page_label", "Unknown")
            context_parts.append(f"Page Content: {doc.page_content}\nPage Number: {page_num}\nFile: {filename}")
            sources.append(page_num)
            
        context = "\n\n---\n\n".join(context_parts)
        
        # Unique and sorted sources
        unique_sources = sorted(list(set(sources)), key=lambda x: int(x) if x.isdigit() else 999)
        
        system_prompt = f"""You are a helpful AI Assistant who answers user queries based on the available context retrieved from a PDF file.

You must only answer the user based on the following context. If the query cannot be answered using the context, state that you do not have sufficient information.
Navigate the user to open the right page numbers to know more.

Context:
{context}
"""
        # Call Groq LLM with Gemini fallback
        llm_response = call_llm(system_prompt, user_query)
        
        # Update chats count in DB
        db = load_documents_db()
        for doc in db:
            if doc["filename"] == filename:
                doc["chats"] = doc.get("chats", 0) + 1
                doc["last_activity"] = datetime.now().strftime("%b %d, %Y %I:%M %p")
                break
        save_documents_db(db)
        
        return {
            "answer": llm_response,
            "sources": unique_sources
        }
        
    except Exception as e:
        print(f"Error querying RAG for {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"RAG engine error: {str(e)}")

def call_llm(system_prompt: str, user_query: str):
    # Try Groq API
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        try:
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
            print(f"Groq API call failed: {e}. Trying fallback...")
            
    # Try Gemini API
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config={"temperature": 0.2}
            )
            
            # Combine system instruction and query
            full_prompt = f"{system_prompt}\n\nUser Question:\n{user_query}"
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            print(f"Gemini API call failed: {e}")
            
    return "Error: Unable to connect to LLM APIs (Both Groq and Gemini calls failed or are unconfigured)."

# Seed documents on startup if empty
def seed_documents():
    # Look at Agentic_Ai/RAG folder for any PDFs we can copy
    rag_dir = r"d:\Codes\anaconda\Agentic_Ai\RAG"
    if not os.path.exists(rag_dir):
        return
        
    db = load_documents_db()
    if len(db) > 0:
        return # already seeded or contains uploads
        
    seeded = False
    for filename in os.listdir(rag_dir):
        if filename.endswith(".pdf"):
            src_path = os.path.join(rag_dir, filename)
            dest_path = os.path.join(DATA_DIR, filename)
            
            try:
                # Copy file
                shutil.copy2(src_path, dest_path)
                file_size_formatted = format_size(os.path.getsize(dest_path))
                
                # Setup basic entry (will be indexed on first load or in background)
                db.append({
                    "filename": filename,
                    "size": file_size_formatted,
                    "pages": 0, # lazy load
                    "date": datetime.now().strftime("%b %d, %Y"),
                    "chats": 0
                })
                seeded = True
                print(f"Seeded document: {filename}")
            except Exception as e:
                print(f"Failed to seed document {filename}: {e}")
                
    if seeded:
        save_documents_db(db)

# Run seed function
seed_documents()

# Serve other static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
