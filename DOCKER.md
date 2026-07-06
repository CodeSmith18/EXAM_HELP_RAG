# Docker Setup

This project can run as one full-stack app container plus a Postgres container.

## 1. Configure secrets

Create a local `.env` file or export these variables before starting Docker:

```bash
GROQ_API_KEY=your_groq_api_key_here
AUTH_SECRET_KEY=replace-with-a-long-random-secret
```

## 2. Start the app

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000
```

The app container serves the built React frontend and FastAPI backend from the same port.

## 3. Data persistence

Docker Compose creates two named volumes:

- `app_data` for uploaded PDFs, FAISS vectors, and HuggingFace model cache.
- `postgres_data` for Postgres data.

## 4. Stop services

```bash
docker compose down
```

To remove volumes too:

```bash
docker compose down -v
```
