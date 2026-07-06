FROM node:22-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VECTOR_DB_PATH=/data/vector_store
ENV DATABASE_URL=sqlite:////data/examprep.sqlite3
ENV UPLOAD_DIR=/data/uploads
ENV EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENV CHUNK_SIZE=900
ENV CHUNK_OVERLAP=125
ENV MAX_UPLOAD_MB=25
ENV MAX_UPLOAD_FILES=5
ENV AUTH_SECRET_KEY=change-this-local-dev-secret
ENV ACCESS_TOKEN_MINUTES=10080
ENV HF_HOME=/data/huggingface
ENV TRANSFORMERS_CACHE=/data/huggingface

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY --from=frontend-build /app/frontend/dist frontend/dist
RUN mkdir -p /data/uploads /data/vector_store /data/huggingface \
    && useradd --create-home --shell /bin/sh appuser \
    && chown -R appuser:appuser /app /data

EXPOSE 8000

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5)"

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --app-dir backend"]
