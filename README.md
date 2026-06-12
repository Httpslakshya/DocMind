# 🧠 DocMind

> Chat with PDFs, generate summaries, notes, quizzes, and retrieve context-aware answers using AI.

![Python](https://img.shields.io/badge/Python-FastAPI-blue)
![React](https://img.shields.io/badge/React-Vite-61DAFB)
![Qdrant](https://img.shields.io/badge/VectorDB-Qdrant-red)
![Supabase](https://img.shields.io/badge/Storage-Supabase-green)
![Gemini](https://img.shields.io/badge/AI-Google_Gemini-orange)

---

## 🚀 Overview

DocMind is an AI-powered document intelligence platform that transforms static PDFs into interactive knowledge sources.

Users can upload PDF documents and:

* 💬 Chat with PDFs using natural language
* 📝 Generate summaries
* 📚 Create study notes
* ❓ Generate quizzes
* 🔍 Perform semantic search
* 📖 Get citation-backed answers
* ☁️ Store and manage documents in the cloud

---

## ✨ Features

* PDF Upload & Management
* AI Chat with Documents
* Citation-Based Responses
* Semantic Search
* Automatic Summarization
* Quiz Generation
* Notes Generation
* Cloud Storage Integration
* Background Document Indexing
* Real-Time Indexing Progress Tracking
* Vector Search using Qdrant Cloud

---

## 🏗️ Architecture

```text
Frontend (Vercel)
        │
        ▼
React + Vite
        │
        ▼
FastAPI Backend (Render)
        │
 ┌──────┼─────────┐
 ▼      ▼         ▼
Supabase   Qdrant   Gemini
Storage    Cloud    Embeddings
```

---

## 🛠️ Tech Stack

### Frontend

* React
* Vite
* JavaScript

### Backend

* Python
* FastAPI
* Uvicorn

### AI & RAG

* Google Gemini Embeddings
* LangChain
* Qdrant Cloud

### Storage

* Supabase Storage
* Supabase Database

### Deployment

* Vercel
* Render

---

## 📂 Project Structure

```text
DocMind/
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── vite.config.js
│
├── backend/
│   ├── api/
│   ├── services/
│   ├── storage/
│   ├── vectorstore/
│   ├── models/
│   └── main.py
│
├── data/
├── logs/
└── README.md
```

---

## 🔄 Document Processing Flow

```text
Upload PDF
     │
     ▼
Supabase Storage
     │
     ▼
PDF Parsing (PyPDFLoader)
     │
     ▼
Chunk Generation
     │
     ▼
Gemini Embeddings
     │
     ▼
Qdrant Vector Indexing
     │
     ▼
Ready for AI Chat
```

---

## 🔐 Security

* Session-based authentication
* CORS protection
* Environment variable configuration
* Secure API key handling
* Backend-only access to AI services

---

## 🚨 Challenges Solved

| Problem                          | Solution                                            |
| -------------------------------- | --------------------------------------------------- |
| Memory crashes on deployment     | Migrated from local embedding models to Gemini API  |
| Lost indexing jobs after restart | Persistent job tracking                             |
| Vector dimension mismatch        | Recreated Qdrant collection with correct dimensions |
| Cross-origin deployment issues   | Production-ready CORS configuration                 |

---

## 📈 Future Roadmap

* Multi-user accounts
* OCR support for scanned PDFs
* Voice-based PDF interaction
* Flashcard generation
* PDF citation highlighting
* Collaborative workspaces
* Mobile application

---

## 🌐 Deployment

### Frontend

Vercel

### Backend

Render

### Storage

Supabase

### Vector Database

Qdrant Cloud

### AI Model

Google Gemini

---

## 👨‍💻 Author

**Lakshya Dharkar**

B.Tech Computer Science Student
AI/ML Enthusiast • Full Stack Developer • Building AI-powered products

---

⭐ If you found this project interesting, consider giving it a star.
