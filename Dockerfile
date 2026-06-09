FROM node:22-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VECTOR_DB_PATH=/tmp/examprep-rag/vector_store
ENV DATABASE_URL=sqlite:////tmp/examprep-rag/examprep.sqlite3
ENV UPLOAD_DIR=/tmp/examprep-rag/uploads
ENV EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENV CHUNK_SIZE=900
ENV CHUNK_OVERLAP=125

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend-build /app/frontend/dist frontend/dist

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir backend"]
