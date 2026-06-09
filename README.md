# ExamPrep RAG: AI-Powered PDF Study Assistant

A full-stack MVP for exam preparation from uploaded PDF notes. Students can upload PDFs, ingest them into a local vector store, generate MCQ or written tests, submit answers, get scores and feedback, and use study mode for simple explanations with optional Mermaid diagrams.

This project uses free or open-source friendly tools and does not use paid OpenAI APIs.

## Tech Stack

- Frontend: React, Vite, TypeScript, Tailwind CSS
- Backend: Python FastAPI
- LLM: Groq API free tier
- RAG: LangChain text splitting and retrieval flow
- PDF parsing: PyMuPDF
- Embeddings: HuggingFace `sentence-transformers/all-MiniLM-L6-v2`
- Vector database: FAISS persisted locally
- App database: SQLite
- Diagrams: Mermaid.js

## Folder Structure

```text
.
|-- .env.example
|-- README.md
|-- backend
|   |-- requirements.txt
|   |-- app
|   |   |-- config.py
|   |   |-- database.py
|   |   |-- main.py
|   |   |-- models.py
|   |   |-- prompts.py
|   |   `-- services
|   |       |-- groq_client.py
|   |       |-- pdf_loader.py
|   |       |-- rag.py
|   |       |-- test_service.py
|   |       `-- vector_store.py
|   `-- data
|       |-- uploads
|       `-- vector_store
`-- frontend
    |-- package.json
    |-- tailwind.config.js
    `-- src
        |-- api.ts
        |-- App.tsx
        |-- components
        `-- pages
```

## Setup

1. Create the environment file:

```bash
cp .env.example .env
```

2. Add your Groq key:

```bash
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

You can switch `GROQ_MODEL` to another Groq-supported free-tier model if your account exposes it.

## Run Backend

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

The API runs at:

```text
http://localhost:8000
```

Useful API docs:

```text
http://localhost:8000/docs
```

## Run Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The app runs at:

```text
http://localhost:5173
```

## Backend Endpoints

- `POST /upload-pdf`
- `GET /documents`
- `POST /ingest-document`
- `POST /generate-test`
- `POST /submit-mcq-test`
- `POST /evaluate-written-test`
- `POST /study-mode`
- `POST /ask-question`
- `GET /health`

## Sample PDF Testing

1. Start the backend and frontend.
2. Open `http://localhost:5173`.
3. Go to Upload and select one or more small text-based PDFs.
4. Wait for ingestion to finish. The backend extracts page text, chunks it, embeds chunks, stores metadata in SQLite, and persists the FAISS index.
5. Go to Generate Test.
6. Choose all ready PDFs or select specific PDFs, then choose MCQ, written, or mixed mode, set question count and difficulty, then generate.
7. Submit answers on Take Test and review scores on Results.
8. Use Study Mode with all ready PDFs or selected PDFs. If the topic has a flow or relationship, the app can render a Mermaid diagram.

Scanned image-only PDFs need OCR before upload because this MVP extracts selectable PDF text.

## RAG Pipeline

1. PDF upload saves the file under `backend/data/uploads`.
2. PyMuPDF extracts text page by page.
3. Text is cleaned and split with LangChain `RecursiveCharacterTextSplitter`.
4. Chunks use about 900 characters with 125 characters of overlap.
5. HuggingFace sentence-transformer embeddings are generated locally.
6. FAISS stores vectors in `backend/data/vector_store`.
7. SQLite stores document metadata, page numbers, chunk ids, and chunk text.
8. Retrieval uses semantic similarity over FAISS and returns source metadata.
9. Prompt templates in `backend/app/prompts.py` force the model to use only retrieved PDF context.
10. Groq returns structured JSON for tests, evaluation, study mode, and Q&A.

## Interview Explanation

This app demonstrates a complete source-aware RAG workflow:

- PDF ingestion turns unstructured notes into page-linked chunks.
- Embeddings convert chunks into semantic vectors.
- FAISS enables fast top-k retrieval for a question or topic.
- Retrieved context is sent to Groq with strict prompts.
- MCQs are scored deterministically in the backend.
- Test generation can be filtered to one or more selected PDFs using chunk metadata.
- Study Mode and PDF Q&A can be filtered to one or more selected PDFs using the same retrieval filter.
- Written answers are evaluated with a rubric for correctness, completeness, and clarity.
- Study mode turns retrieved context into exam-friendly revision notes and diagrams.

The system is intentionally simple: local SQLite and local FAISS make the MVP easy to explain, run, and extend.

## Free Deployment Suggestions

- Frontend: Vercel, Netlify, or Cloudflare Pages.
- Backend: Render free tier, Fly.io, Railway hobby/free credits, or a small VM.
- Database: SQLite for demos; move to Postgres if deploying for multiple users.
- Vector store: local FAISS for MVP; ChromaDB, Qdrant, or hosted vector storage for larger deployments.
- Models: Groq free tier for LLM calls and local HuggingFace embeddings.

## Render Deployment

This repo includes `render.yaml` for Render Blueprint deployment. See `RENDER_DEPLOYMENT.md` for step-by-step setup.

For deployment, set these environment variables on the backend host:

```bash
GROQ_API_KEY=...
GROQ_MODEL=llama-3.1-8b-instant
VECTOR_DB_PATH=backend/data/vector_store
DATABASE_URL=sqlite:///backend/data/examprep.sqlite3
UPLOAD_DIR=backend/data/uploads
```

Set this on the frontend host:

```bash
VITE_API_BASE_URL=https://your-backend-url
```
# EXAM_HELP_RAG
