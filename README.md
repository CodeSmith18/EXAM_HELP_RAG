# ExamHelp RAG

AI-powered PDF study assistant for generating tests, revision notes, written-answer feedback, and source-grounded Q&A from uploaded study material.

![React](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![RAG](https://img.shields.io/badge/AI-RAG%20%2B%20FAISS-6C63FF?style=for-the-badge)
![Groq](https://img.shields.io/badge/LLM-Groq%20API-F55036?style=for-the-badge)

## Overview

ExamHelp RAG is a full-stack RAG application that converts uploaded PDFs into an interactive exam-preparation workspace. Students can upload notes, generate MCQ or written tests, get scores and feedback, ask questions from selected documents, and create study notes grounded in their own PDF content.

The project focuses on practical backend and AI engineering:

- PDF ingestion, parsing, chunking, embedding, and vector search.
- Source-aware retrieval using FAISS and document-level filters.
- Structured LLM workflows for MCQs, written evaluation, study notes, and Q&A.
- Full-stack user flow with React, FastAPI, SQLite, and local vector persistence.

## Preview

| Dashboard | Upload |
| --- | --- |
| ![ExamHelp RAG dashboard](docs/screenshots/examprep-rag-dashboard.png) | ![ExamHelp RAG upload screen](docs/screenshots/examprep-rag-upload.png) |

| Documents | Tests |
| --- | --- |
| ![ExamHelp RAG documents screen](docs/screenshots/examprep-rag-documents.png) | ![ExamHelp RAG tests screen](docs/screenshots/examprep-rag-tests.png) |

| Study Mode |
| --- |
| ![ExamHelp RAG study screen](docs/screenshots/examprep-rag-study.png) |

## Key Features

- Upload and manage text-based PDF study material.
- Parse PDFs into page-linked chunks for traceable retrieval.
- Generate MCQ, written, or mixed tests from selected documents.
- Evaluate MCQ answers deterministically in the backend.
- Evaluate written answers with rubric-based LLM feedback.
- Ask document-grounded questions using FAISS top-k retrieval.
- Generate exam-focused study notes from uploaded PDFs.
- Render Mermaid diagrams for flow-based study topics.
- Persist document metadata in SQLite and vector indexes in FAISS.

## Architecture

```mermaid
flowchart LR
    A[PDF Upload] --> B[PyMuPDF Text Extraction]
    B --> C[Chunking with Overlap]
    C --> D[Sentence Transformer Embeddings]
    D --> E[FAISS Vector Store]
    C --> F[SQLite Metadata]
    G[User Query or Test Request] --> H[Filtered Retrieval]
    E --> H
    F --> H
    H --> I[Prompt Templates]
    I --> J[Groq LLM]
    J --> K[Tests, Notes, Feedback, Q&A]
```

## Tech Stack

| Area | Tools |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, Mermaid.js |
| Backend | FastAPI, Python, Pydantic Settings |
| AI / RAG | LangChain, FAISS, HuggingFace sentence-transformers, Groq API |
| Database | SQLite, local FAISS persistence |
| PDF Processing | PyMuPDF |
| Deployment | Docker, Render Blueprint |

## Backend API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/upload-pdf` | Upload a PDF document |
| `GET` | `/documents` | List uploaded documents |
| `POST` | `/ingest-document` | Parse, chunk, embed, and index a document |
| `POST` | `/generate-test` | Generate MCQ, written, or mixed tests |
| `POST` | `/submit-mcq-test` | Score MCQ answers |
| `POST` | `/evaluate-written-test` | Evaluate written answers |
| `POST` | `/study-mode` | Generate study notes |
| `POST` | `/ask-question` | Ask questions from selected PDFs |
| `GET` | `/health` | Health check |

## Getting Started

### 1. Clone and configure

```bash
git clone https://github.com/CodeSmith18/EXAM_HELP_RAG.git
cd EXAM_HELP_RAG
cp .env.example .env
```

Update `.env` with your Groq API key:

```bash
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
AUTH_SECRET_KEY=replace-with-a-long-random-secret
```

### 2. Run with Docker

Docker is the easiest way to start the full project. It runs:

- FastAPI backend
- Built React frontend
- Postgres database
- Persistent volumes for uploads, FAISS vectors, model cache, and database data

Start everything:

```bash
docker compose up --build
```

Open the app:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

Stop containers:

```bash
docker compose down
```

Remove containers and local Docker volumes:

```bash
docker compose down -v
```

See `DOCKER.md` for a shorter Docker-only guide.

### 3. Run without Docker

Run the backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

Backend URL:

```text
http://localhost:8000
```

API docs:

```text
http://localhost:8000/docs
```

Run the frontend:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:5173
```

## Environment Variables

```bash
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
VECTOR_DB_PATH=backend/data/vector_store
DATABASE_URL=sqlite:///backend/data/examprep.sqlite3
UPLOAD_DIR=backend/data/uploads
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=900
CHUNK_OVERLAP=125
MAX_UPLOAD_MB=25
MAX_UPLOAD_FILES=5
AUTH_SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_MINUTES=10080
VITE_API_BASE_URL=http://localhost:8000
```

For Docker Compose, the app service uses Postgres automatically:

```bash
DATABASE_URL=postgresql://examprep:examprep_dev_password@postgres:5432/examprep
```

## Project Structure

```text
.
|-- backend
|   |-- app
|   |   |-- main.py
|   |   |-- models.py
|   |   |-- prompts.py
|   |   `-- services
|   |       |-- groq_client.py
|   |       |-- pdf_loader.py
|   |       |-- rag.py
|   |       |-- test_service.py
|   |       `-- vector_store.py
|   |-- data
|   `-- requirements.txt
|-- frontend
|   |-- src
|   |   |-- components
|   |   |-- pages
|   |   |-- api.ts
|   |   `-- App.tsx
|   `-- package.json
|-- docs
|   `-- screenshots
|-- DOCKER.md
|-- Dockerfile
|-- docker-compose.yml
|-- render.yaml
`-- README.md
```

## RAG Pipeline

1. The user uploads one or more PDF files.
2. The backend stores uploaded files under `backend/data/uploads`.
3. PyMuPDF extracts selectable text page by page.
4. LangChain splits text into chunks of about 900 characters with 125 characters of overlap.
5. HuggingFace sentence-transformer embeddings are generated locally.
6. FAISS stores vectors under `backend/data/vector_store`.
7. SQLite stores document metadata, chunk text, page numbers, and chunk ids.
8. User requests retrieve the most relevant chunks with optional document-level filtering.
9. Prompt templates instruct the LLM to answer only from retrieved context.
10. Groq returns structured output for tests, evaluations, notes, and Q&A.

## What This Project Demonstrates

- End-to-end RAG application design.
- Backend API design with FastAPI.
- Vector search and metadata-filtered retrieval.
- LLM prompt design for structured JSON responses.
- PDF processing and text chunking strategy.
- Local persistence using SQLite and FAISS.
- Full-stack product flow from upload to AI-generated output.

## Limitations

- Scanned image-only PDFs require OCR before upload.
- Local FAISS and SQLite are optimized for demos and MVP usage.
- For multi-user production deployment, move the database to Postgres and use a hosted vector database such as Qdrant, ChromaDB, or Pinecone.

## Deployment

This repo includes `render.yaml` for Render Blueprint deployment. See `RENDER_DEPLOYMENT.md` for the full deployment steps.

For deployment, configure backend environment variables on the hosting platform and set the frontend API URL:

```bash
VITE_API_BASE_URL=https://your-backend-url
```
