from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.config import get_settings
from app.models import (
    AskQuestionRequest,
    AskQuestionResponse,
    DocumentOut,
    EvaluateWrittenRequest,
    EvaluateWrittenResponse,
    GenerateTestRequest,
    GenerateTestResponse,
    IngestRequest,
    StudyModeRequest,
    StudyModeResponse,
    SubmitMcqRequest,
    SubmitMcqResponse,
    UploadResponse,
)
from app.services import rag
from app.services.test_service import evaluate_written_test, generate_test, score_mcq_test


app = FastAPI(title="ExamPrep RAG API", version="1.0.0")
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    database.init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(files: list[UploadFile] = File(...)) -> UploadResponse:
    documents: list[DocumentOut] = []
    for file in files:
        document_id, _ = await rag.save_upload(file)
        ingested = rag.ingest_document(document_id)
        documents.append(DocumentOut(**ingested))
    return UploadResponse(documents=documents)


@app.get("/documents", response_model=list[DocumentOut])
def documents() -> list[DocumentOut]:
    return [DocumentOut(**document) for document in database.list_documents()]


@app.post("/ingest-document", response_model=DocumentOut)
def ingest_document(request: IngestRequest) -> DocumentOut:
    document = rag.ingest_document(request.document_id)
    return DocumentOut(**document)


@app.post("/generate-test", response_model=GenerateTestResponse)
async def generate_test_endpoint(request: GenerateTestRequest) -> GenerateTestResponse:
    response = await generate_test(request)
    if not response.questions:
        raise HTTPException(status_code=404, detail="No relevant content was found in the uploaded PDF.")
    return response


@app.post("/submit-mcq-test", response_model=SubmitMcqResponse)
def submit_mcq_test(request: SubmitMcqRequest) -> SubmitMcqResponse:
    return score_mcq_test(request)


@app.post("/evaluate-written-test", response_model=EvaluateWrittenResponse)
async def evaluate_written_endpoint(request: EvaluateWrittenRequest) -> EvaluateWrittenResponse:
    return await evaluate_written_test(request)


@app.post("/study-mode", response_model=StudyModeResponse)
async def study_mode(request: StudyModeRequest) -> StudyModeResponse:
    return StudyModeResponse(**await rag.study_topic(request.topic, request.include_diagram, request.document_ids))


@app.post("/ask-question", response_model=AskQuestionResponse)
async def ask_question(request: AskQuestionRequest) -> AskQuestionResponse:
    answer, sources = await rag.ask_question(request.question, request.top_k, request.document_ids)
    return AskQuestionResponse(answer=answer, sources=sources)
