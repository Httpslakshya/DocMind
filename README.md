# DocMind: AI-Powered PDF Chat Application

DocMind is a Neubrutalist cited PDF chat application that lets users upload documents, automatically chunks and indexes them, and utilizes RAG (Retrieval-Augmented Generation) to answer questions with clickable page-level source highlights.

This repository separates the codebase into a decoupled Full-Stack architecture suitable for production deployment:
* **Frontend**: HTML5/CSS3/JavaScript Multi-Page Application powered by **Vite** (Deploys to **Vercel**).
* **Backend**: **FastAPI** Python service with modular routers and abstract storage providers (Deploys to **Render**).

---

## Workspace Layout

```text
DocMind/
├── frontend/                  # Decoupled Static Frontend
│   ├── public/                # Static assets (logos, images)
│   ├── src/                   # Modular JavaScript modules
│   │   ├── api.js             # Global HTTP Fetch Wrapper
│   │   ├── login.js           # Auth validations and handlers
│   │   ├── dashboard.js       # File catalogs and uploads UI
│   │   ├── processing.js      # Upload stream progress tracking
│   │   ├── chat.js            # Chat view & cited page highlight logic
│   │   └── document.js        # Detailed metadata readout UI
│   ├── index.html             # Login Entry point (renamed from login.html)
│   ├── dashboard.html         # User document library
│   ├── processing.html        # Loading & vectorizing page
│   ├── chat.html              # Multi-pane conversation workspace
│   ├── document.html          # Detailed document readout
│   ├── package.json           # Vite builder dependencies
│   ├── vite.config.js         # Rollup MPA config
│   └── vercel.json            # Vercel rewrites rules
│
├── backend/                   # Decoupled FastAPI Server
│   ├── api/                   # Router endpoints
│   │   ├── auth.py            # Login, logout, session check
│   │   ├── chat.py            # RAG conversation logic
│   │   └── documents.py       # Catalog query, upload, delete
│   ├── config/
│   │   └── settings.py        # Environmental configuration loader
│   ├── middleware/
│   │   └── security.py        # Dynamic CORS configuration
│   ├── models/
│   │   └── schemas.py         # Standardized Pydantic models & responses
│   ├── services/
│   │   └── rag.py             # Embeddings, chunking, LLM routers
│   ├── storage/               # Abstract Storage Layer
│   │   ├── base.py            # Storage Abstract Base Class
│   │   ├── local.py           # Disk storage driver
│   │   └── service.py         # Provider selector singleton
│   ├── utils/
│   │   ├── helpers.py         # Size formatting, filename sanitization
│   │   └── logging_config.py  # Production rotating file logger
│   ├── vectorstore/
│   │   └── qdrant.py          # Qdrant client connection pool
│   ├── logs/                  # Application runtime log files
│   ├── render.yaml            # Render infrastructure blueprint
│   ├── requirements.txt       # Backend Python packages
│   ├── test_api.py            # In-memory integration test suite
│   └── main.py                # Server entryway
│
├── .env.example               # Root configuration env template
└── README.md                  # System manual and deployment guide
```

---

## Environment Configuration

### Frontend Settings (`frontend/.env`)
Create `frontend/.env` pointing to the backend API endpoint:
```env
VITE_API_URL=http://localhost:8000
```

### Backend Settings (`.env` in the root)
Create `.env` containing keys for services:
```env
ENVIRONMENT=development
FRONTEND_URL=http://localhost:5173

QDRANT_URL=https://your-qdrant-cluster.aws.cloud.qdrant.io
QDRANT_API_KEY=your-api-key

GROQ_API_KEY=your-groq-key
GEMINI_API_KEY=your-gemini-fallback-key

STORAGE_BACKEND=local
```

---

## Local Development Setup

### 1. Run the Backend API
From the repository root:
```bash
# Create a virtual environment and activate it
python -m venv .venv
# On Windows:
.venv\Scripts\activate

# Install requirements
pip install -r backend/requirements.txt

# Run server (runs on port 8000)
python backend/main.py
```

### 2. Run Frontend Dev Server
From the `frontend` folder:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## Deployment Playbooks

### Frontend Deployment: Vercel
1. Install [Vercel CLI](https://vercel.com/cli) or hook your GitHub repo to the Vercel dashboard.
2. Set the build parameters:
   * **Framework Preset**: `Vite` (or `Other`)
   * **Root Directory**: `frontend`
   * **Build Command**: `npm run build`
   * **Output Directory**: `dist`
3. Configure Environment Variables:
   * Add `VITE_API_URL` pointing to your deployed Render URL (e.g. `https://docmind-backend.onrender.com`).
4. Click **Deploy**.

### Backend Deployment: Render
1. Render automatically reads the blueprint inside `backend/render.yaml`.
2. Connect your GitHub repository to Render.
3. Select **New** > **Blueprint** on your dashboard.
4. Render will create the service named `docmind-backend` with:
   * **Build Command**: `pip install -r backend/requirements.txt`
   * **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Render will prompt you to provide values for the missing environment variables (`QDRANT_URL`, `QDRANT_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, and `FRONTEND_URL` pointing to your Vercel domain).
6. Deploy the service.

---

## Security Features Included

* **Sanitized Filenames**: Strip path traversal indicators (`../`) and non-alphanumeric characters.
* **MIME Verification**: Validate content headers ensuring only real `application/pdf` streams are processed.
* **File Sizing Enforcements**: Configurable file bounds checking rejecting uploads exceeding 15MB.
* **CORS Limits**: Allowed origins restricted in production.
* **Abstract Storage Interface**: Business logic decoupled from disk interactions, facilitating S3/Supabase swaps.
* **Structured Logs**: Multi-handler logging rotating up to 10MB to maintain clean, searchable operations.
