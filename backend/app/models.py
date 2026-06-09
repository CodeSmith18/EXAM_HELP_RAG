from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


TestMode = Literal["mcq", "written", "mixed"]
Difficulty = Literal["Easy", "Medium", "Hard"]


class DocumentOut(BaseModel):
    id: str
    file_name: str
    uploaded_at: str
    page_count: int
    chunk_count: int
    status: str
    error: Optional[str] = None


class UploadResponse(BaseModel):
    documents: list[DocumentOut]


class IngestRequest(BaseModel):
    document_id: str


class SourceRef(BaseModel):
    document_id: str
    file_name: str
    page_number: int
    chunk_id: str
    score: Optional[float] = None


class GenerateTestRequest(BaseModel):
    mode: TestMode
    num_questions: int = Field(default=5, ge=1, le=25)
    difficulty: Difficulty = "Medium"
    topic: Optional[str] = None
    document_ids: list[str] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    id: str
    type: Literal["mcq", "written"]
    question: str
    options: list[str] = Field(default_factory=list)
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    model_answer: Optional[str] = None
    rubric: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)


class GenerateTestResponse(BaseModel):
    test_id: str
    mode: TestMode
    difficulty: Difficulty
    topic: Optional[str] = None
    questions: list[GeneratedQuestion]
    sources: list[SourceRef]


class McqAnswer(BaseModel):
    question_id: str
    selected_answer: str


class SubmitMcqRequest(BaseModel):
    questions: list[GeneratedQuestion]
    answers: list[McqAnswer]


class McqResultItem(BaseModel):
    question_id: str
    question: str
    selected_answer: str
    correct_answer: str
    is_correct: bool
    explanation: Optional[str] = None


class SubmitMcqResponse(BaseModel):
    score: int
    total: int
    percentage: float
    results: list[McqResultItem]


class WrittenAnswer(BaseModel):
    question_id: str
    answer: str


class EvaluateWrittenRequest(BaseModel):
    questions: list[GeneratedQuestion]
    answers: list[WrittenAnswer]


class WrittenEvaluationItem(BaseModel):
    question_id: str
    question: str
    score: float
    max_score: float = 10
    feedback: str
    model_answer: str
    rubric_breakdown: dict[str, Any] = Field(default_factory=dict)
    sources: list[SourceRef] = Field(default_factory=list)


class EvaluateWrittenResponse(BaseModel):
    score: float
    max_score: float
    percentage: float
    results: list[WrittenEvaluationItem]


class StudyModeRequest(BaseModel):
    topic: str
    include_diagram: bool = True
    document_ids: list[str] = Field(default_factory=list)


class StudyModeResponse(BaseModel):
    topic: str
    simple_explanation: str
    key_points: list[str]
    example: Optional[str] = None
    important_terms: list[dict[str, str]] = Field(default_factory=list)
    quick_revision_summary: str
    mermaid_diagram: Optional[str] = None
    sources: list[SourceRef]


class AskQuestionRequest(BaseModel):
    question: str
    top_k: int = Field(default=6, ge=1, le=12)
    document_ids: list[str] = Field(default_factory=list)


class AskQuestionResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
