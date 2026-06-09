# Deploying ExamPrep RAG on Render

This repo is ready for Render Blueprint deployment with `render.yaml`.

## What Render Will Create

- `examprep-rag-api`: FastAPI backend web service
- `examprep-rag-web`: React/Vite static frontend

The frontend receives the backend host through `VITE_API_BASE_URL`, and the backend receives the frontend host through `FRONTEND_ORIGIN`.

## Steps

1. Push this repository to GitHub.
2. Open Render Dashboard.
3. Choose **New +** -> **Blueprint**.
4. Connect the GitHub repo.
5. Render detects `render.yaml`.
6. When prompted, enter `GROQ_API_KEY`.
7. Deploy the Blueprint.

## Backend Settings

Render uses:

```bash
Root Directory: backend
Build Command: pip install --upgrade pip && pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

Important environment variables:

```bash
GROQ_API_KEY=<set in Render dashboard>
GROQ_MODEL=llama-3.1-8b-instant
PYTHON_VERSION=3.11.11
VECTOR_DB_PATH=/tmp/examprep-rag/vector_store
DATABASE_URL=sqlite:////tmp/examprep-rag/examprep.sqlite3
UPLOAD_DIR=/tmp/examprep-rag/uploads
```

## Frontend Settings

Render uses:

```bash
Root Directory: frontend
Build Command: npm ci && npm run build
Publish Directory: dist
```

The SPA rewrite is configured so routes like `/study` and `/generate-test` work after refresh.

## Free Tier Note

The default blueprint uses `/tmp` storage so it can deploy on Render's free web service plan. Uploaded PDFs, SQLite data, and FAISS indexes can disappear after service restarts or redeploys.

For a longer-lived demo, upgrade the backend to a paid web service and attach a persistent disk. Then change these backend environment variables:

```bash
VECTOR_DB_PATH=/var/data/vector_store
DATABASE_URL=sqlite:////var/data/examprep.sqlite3
UPLOAD_DIR=/var/data/uploads
```

Attach the disk at:

```bash
Mount Path: /var/data
```

## Manual Deployment Alternative

If you do not use Blueprint, create two Render services manually:

1. Web Service for backend:
   - Runtime: Python
   - Root Directory: `backend`
   - Build Command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

2. Static Site for frontend:
   - Root Directory: `frontend`
   - Build Command: `npm ci && npm run build`
   - Publish Directory: `dist`
   - Add rewrite: `/*` -> `/index.html`

Set `VITE_API_BASE_URL` to the backend Render host or full backend URL, and set `FRONTEND_ORIGIN` on the backend to the frontend Render host or full frontend URL.

