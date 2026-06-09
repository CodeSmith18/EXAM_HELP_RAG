# Deploying ExamPrep RAG on Render

This repo is ready for a single Render Web Service deployment.

The Docker build does both jobs:

- Builds the React frontend into `frontend/dist`
- Installs the FastAPI backend
- Runs FastAPI, which serves both the API and the built frontend

## Recommended: One Render Web Service

Use this when you want one deployment URL for the whole app.

### Steps

1. Push this repository to GitHub.
2. Open Render Dashboard.
3. Choose **New +** -> **Web Service**.
4. Connect the GitHub repo.
5. Fill the service settings:

```text
Name: exam-help-rag
Language: Docker
Branch: main
Root Directory: leave empty
Dockerfile Path: ./Dockerfile
```

6. Add environment variables:

```bash
GROQ_API_KEY=<your Groq key>
GROQ_MODEL=llama-3.1-8b-instant
VECTOR_DB_PATH=/tmp/examprep-rag/vector_store
DATABASE_URL=sqlite:////tmp/examprep-rag/examprep.sqlite3
UPLOAD_DIR=/tmp/examprep-rag/uploads
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=900
CHUNK_OVERLAP=125
```

7. Deploy.

After deploy, open the single Render service URL. The frontend and backend are served from the same origin, so no `VITE_API_BASE_URL` or CORS setup is needed for this one-service Docker deployment.

## Blueprint Option

This repo also includes `render.yaml`, so you can use:

```text
New + -> Blueprint
```

Render will create one Docker web service from the same `Dockerfile`.

## How It Works

The `Dockerfile` uses a two-stage build:

```text
Stage 1: node:22-slim builds frontend/dist
Stage 2: python:3.11-slim installs backend and copies frontend/dist
```

FastAPI serves React routes from `frontend/dist`. API routes like `/upload-pdf`, `/generate-test`, `/study-mode`, and `/ask-question` still work normally.

## Free Tier Note

The default deployment uses `/tmp` storage so it can run on Render's free plan. Uploaded PDFs, SQLite data, and FAISS indexes can disappear after restarts or redeploys.

For persistent storage, upgrade to a paid web service and attach a persistent disk. Then change the backend environment variables:

```bash
VECTOR_DB_PATH=/var/data/vector_store
DATABASE_URL=sqlite:////var/data/examprep.sqlite3
UPLOAD_DIR=/var/data/uploads
```

Attach the disk at:

```bash
Mount Path: /var/data
```

## Alternative: Two Services

You can still deploy backend and frontend separately:

- Backend: Python Web Service with root directory `backend`
- Frontend: Static Site with root directory `frontend`

But for this project, the single Docker service is simpler.

