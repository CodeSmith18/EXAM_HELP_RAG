from __future__ import annotations

from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app import database
from app.config import PROJECT_ROOT, get_settings
from app.models import (
    AskQuestionRequest,
    AskQuestionResponse,
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthResponse,
    DocumentOut,
    EvaluateWrittenRequest,
    EvaluateWrittenResponse,
    GenerateTestRequest,
    GenerateTestResponse,
    IngestRequest,
    SaveTestResultRequest,
    SavedTestResult,
    StudySessionOut,
    StudyModeRequest,
    StudyModeResponse,
    SubmitMcqRequest,
    SubmitMcqResponse,
    TestHistoryItem,
    UploadResponse,
    UserOut,
)
from app.services import rag
from app.services.auth import get_current_user, login_user, register_user
from app.services.test_service import (
    evaluate_written_test,
    generate_test,
    get_saved_test,
    list_saved_results,
    list_saved_tests,
    save_test_result,
    score_mcq_test,
)


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


@app.post("/auth/register", response_model=AuthResponse)
def register(request: AuthRegisterRequest) -> AuthResponse:
    return register_user(request)


@app.post("/auth/login", response_model=AuthResponse)
def login(request: AuthLoginRequest) -> AuthResponse:
    return login_user(request)


@app.get("/auth/me", response_model=UserOut)
def auth_me(current_user: UserOut = Depends(get_current_user)) -> UserOut:
    return current_user


@app.post("/upload-pdf", response_model=UploadResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    current_user: UserOut = Depends(get_current_user),
) -> UploadResponse:
    rag.validate_upload_batch(files)
    documents: list[DocumentOut] = []
    for file in files:
        document_id, _ = await rag.save_upload(file, owner_id=current_user.id)
        document = database.get_document(document_id, owner_id=current_user.id)
        if document:
            documents.append(DocumentOut(**document))
        background_tasks.add_task(rag.ingest_document, document_id)
    return UploadResponse(documents=documents)


@app.get("/documents", response_model=list[DocumentOut])
def documents(current_user: UserOut = Depends(get_current_user)) -> list[DocumentOut]:
    return [DocumentOut(**document) for document in database.list_documents(owner_id=current_user.id)]


@app.delete("/documents/{document_id}", response_model=DocumentOut)
def delete_document(document_id: str, current_user: UserOut = Depends(get_current_user)) -> DocumentOut:
    document = database.delete_document(document_id, owner_id=current_user.id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    Path(document["stored_path"]).unlink(missing_ok=True)
    rag.rebuild_vector_store()
    return DocumentOut(**document)


@app.post("/ingest-document", response_model=DocumentOut)
def ingest_document(request: IngestRequest, current_user: UserOut = Depends(get_current_user)) -> DocumentOut:
    if not database.get_document(request.document_id, owner_id=current_user.id):
        raise HTTPException(status_code=404, detail="Document not found.")
    document = rag.ingest_document(request.document_id)
    return DocumentOut(**document)


@app.post("/generate-test", response_model=GenerateTestResponse)
async def generate_test_endpoint(request: GenerateTestRequest, current_user: UserOut = Depends(get_current_user)) -> GenerateTestResponse:
    response = await generate_test(request, owner_id=current_user.id)
    if not response.questions:
        raise HTTPException(status_code=404, detail="No relevant content was found in the uploaded PDF.")
    return response


@app.get("/tests", response_model=list[TestHistoryItem])
def tests(current_user: UserOut = Depends(get_current_user)) -> list[TestHistoryItem]:
    return list_saved_tests(owner_id=current_user.id)


@app.get("/tests/{test_id}", response_model=GenerateTestResponse)
def test_detail(test_id: str, current_user: UserOut = Depends(get_current_user)) -> GenerateTestResponse:
    return get_saved_test(test_id, owner_id=current_user.id)


@app.post("/submit-mcq-test", response_model=SubmitMcqResponse)
def submit_mcq_test(request: SubmitMcqRequest, current_user: UserOut = Depends(get_current_user)) -> SubmitMcqResponse:
    return score_mcq_test(request)


@app.post("/evaluate-written-test", response_model=EvaluateWrittenResponse)
async def evaluate_written_endpoint(
    request: EvaluateWrittenRequest,
    current_user: UserOut = Depends(get_current_user),
) -> EvaluateWrittenResponse:
    return await evaluate_written_test(request, owner_id=current_user.id)


@app.post("/save-test-result", response_model=SavedTestResult)
def save_test_result_endpoint(request: SaveTestResultRequest, current_user: UserOut = Depends(get_current_user)) -> SavedTestResult:
    return save_test_result(request, owner_id=current_user.id)


@app.get("/test-results", response_model=list[SavedTestResult])
def test_results(current_user: UserOut = Depends(get_current_user)) -> list[SavedTestResult]:
    return list_saved_results(owner_id=current_user.id)


@app.post("/study-mode", response_model=StudyModeResponse)
async def study_mode(request: StudyModeRequest, current_user: UserOut = Depends(get_current_user)) -> StudyModeResponse:
    response = StudyModeResponse(
        **await rag.study_topic(request.topic, request.include_diagram, request.document_ids, owner_id=current_user.id)
    )
    database.create_study_session(
        owner_id=current_user.id,
        topic=request.topic,
        include_diagram=request.include_diagram,
        document_ids=request.document_ids,
        response=response.model_dump(mode="json"),
    )
    return response


@app.get("/study-sessions", response_model=list[StudySessionOut])
def study_sessions(current_user: UserOut = Depends(get_current_user)) -> list[StudySessionOut]:
    return [StudySessionOut(**session) for session in database.list_study_sessions(owner_id=current_user.id)]


@app.get("/study-sessions/{session_id}", response_model=StudySessionOut)
def study_session_detail(session_id: str, current_user: UserOut = Depends(get_current_user)) -> StudySessionOut:
    session = database.get_study_session(session_id, owner_id=current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Study session not found.")
    return StudySessionOut(**session)


@app.delete("/study-sessions/{session_id}")
def delete_study_session(session_id: str, current_user: UserOut = Depends(get_current_user)) -> dict[str, bool]:
    if not database.delete_study_session(session_id, owner_id=current_user.id):
        raise HTTPException(status_code=404, detail="Study session not found.")
    return {"deleted": True}


@app.post("/ask-question", response_model=AskQuestionResponse)
async def ask_question(request: AskQuestionRequest, current_user: UserOut = Depends(get_current_user)) -> AskQuestionResponse:
    answer, sources = await rag.ask_question(request.question, request.top_k, request.document_ids, owner_id=current_user.id)
    return AskQuestionResponse(answer=answer, sources=sources)


FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str) -> FileResponse:
    if not FRONTEND_DIST.exists():
        raise HTTPException(status_code=404, detail="Frontend build not found. Run npm run build in frontend/.")

    requested_path = (FRONTEND_DIST / full_path).resolve()
    try:
        requested_path.relative_to(FRONTEND_DIST.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="File not found.") from exc

    if requested_path.is_file():
        return FileResponse(requested_path)

    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend index.html not found.")
