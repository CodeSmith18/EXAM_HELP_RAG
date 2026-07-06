from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


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


class TestHistoryItem(BaseModel):
    test_id: str
    mode: TestMode
    difficulty: Difficulty
    topic: Optional[str] = None
    question_count: int
    created_at: str
    sources: list[SourceRef] = Field(default_factory=list)


class LLMGeneratedQuestion(BaseModel):
    type: Literal["mcq", "written"] = "mcq"
    question: str = Field(min_length=1)
    options: list[str] = Field(default_factory=list)
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    model_answer: Optional[str] = None
    rubric: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_question_shape(self) -> "LLMGeneratedQuestion":
        self.question = self.question.strip()
        if self.type == "mcq":
            self.options = [str(option).strip() for option in self.options if str(option).strip()]
            if len(self.options) != 4:
                raise ValueError("MCQ questions must include exactly 4 options.")
            if self.correct_answer not in self.options:
                raise ValueError("MCQ correct_answer must exactly match one option.")
            return self

        self.options = []
        self.rubric = [str(point).strip() for point in self.rubric if str(point).strip()]
        if not (self.model_answer or "").strip():
            raise ValueError("Written questions must include a model_answer.")
        if not self.rubric:
            raise ValueError("Written questions must include a rubric.")
        return self


class LLMQuestionsPayload(BaseModel):
    questions: list[LLMGeneratedQuestion] = Field(default_factory=list)


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


class LLMWrittenEvaluationPayload(BaseModel):
    score: float
    feedback: str
    model_answer: str
    rubric_breakdown: dict[str, Any] = Field(default_factory=dict)


class SaveTestResultRequest(BaseModel):
    test: GenerateTestResponse
    mcq: Optional[SubmitMcqResponse] = None
    written: Optional[EvaluateWrittenResponse] = None


class SavedTestResult(BaseModel):
    result_id: str
    test: GenerateTestResponse
    mcq: Optional[SubmitMcqResponse] = None
    written: Optional[EvaluateWrittenResponse] = None
    submitted_at: str
    percentage: float


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


class LLMStudyModePayload(BaseModel):
    simple_explanation: str
    key_points: list[str] = Field(default_factory=list)
    example: Optional[str] = None
    important_terms: list[dict[str, str]] = Field(default_factory=list)
    quick_revision_summary: str
    mermaid_diagram: Optional[str] = None


class AskQuestionRequest(BaseModel):
    question: str
    top_k: int = Field(default=6, ge=1, le=12)
    document_ids: list[str] = Field(default_factory=list)


class AskQuestionResponse(BaseModel):
    answer: str
    sources: list[SourceRef]


class LLMAnswerPayload(BaseModel):
    answer: str
