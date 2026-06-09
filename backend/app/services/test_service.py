from __future__ import annotations

import uuid

from app.models import (
    EvaluateWrittenRequest,
    EvaluateWrittenResponse,
    GeneratedQuestion,
    GenerateTestRequest,
    GenerateTestResponse,
    McqResultItem,
    SourceRef,
    SubmitMcqRequest,
    SubmitMcqResponse,
    WrittenEvaluationItem,
)
from app.prompts import MCQ_GENERATION_PROMPT, MIXED_TEST_PROMPT, WRITTEN_EVALUATION_PROMPT, WRITTEN_QUESTION_PROMPT
from app.services.groq_client import GroqClient
from app.services.rag import retrieve_context


def normalize_answer(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lower()
    for prefix in ("a.", "b.", "c.", "d.", "a)", "b)", "c)", "d)"):
        if normalized.startswith(prefix):
            normalized = normalized[2:].strip()
    return " ".join(normalized.split())


def prompt_for_mode(request: GenerateTestRequest, context: str) -> str:
    topic = request.topic or "Any important exam topic from the uploaded PDF"
    if request.mode == "mcq":
        return MCQ_GENERATION_PROMPT.format(
            num_questions=request.num_questions,
            difficulty=request.difficulty,
            topic=topic,
            context=context,
        )
    if request.mode == "written":
        return WRITTEN_QUESTION_PROMPT.format(
            num_questions=request.num_questions,
            difficulty=request.difficulty,
            topic=topic,
            context=context,
        )
    return MIXED_TEST_PROMPT.format(
        num_questions=request.num_questions,
        difficulty=request.difficulty,
        topic=topic,
        context=context,
    )


def normalize_generated_questions(raw_questions: list[dict], sources: list[SourceRef]) -> list[GeneratedQuestion]:
    normalized: list[GeneratedQuestion] = []
    for index, item in enumerate(raw_questions, start=1):
        q_type = item.get("type", "mcq")
        if q_type not in {"mcq", "written"}:
            q_type = "mcq" if item.get("options") else "written"
        options = item.get("options") or []
        if q_type == "mcq":
            options = [str(option) for option in options][:4]
        else:
            options = []
        normalized.append(
            GeneratedQuestion(
                id=f"q{index}",
                type=q_type,
                question=str(item.get("question", "")).strip(),
                options=options,
                correct_answer=item.get("correct_answer"),
                explanation=item.get("explanation"),
                model_answer=item.get("model_answer"),
                rubric=[str(point) for point in item.get("rubric", [])],
                sources=sources[:3],
            )
        )
    return [question for question in normalized if question.question]


async def generate_test(request: GenerateTestRequest) -> GenerateTestResponse:
    query = " ".join(
        [
            request.topic or "important exam concepts",
            request.mode,
            request.difficulty,
            "questions",
        ]
    )
    context, sources = retrieve_context(query, document_ids=request.document_ids)
    if not context:
        return GenerateTestResponse(
            test_id=str(uuid.uuid4()),
            mode=request.mode,
            difficulty=request.difficulty,
            topic=request.topic,
            questions=[],
            sources=[],
        )
    payload = await GroqClient().chat_json(prompt_for_mode(request, context), temperature=0.2)
    questions = normalize_generated_questions(payload.get("questions", []), sources)
    return GenerateTestResponse(
        test_id=str(uuid.uuid4()),
        mode=request.mode,
        difficulty=request.difficulty,
        topic=request.topic,
        questions=questions,
        sources=sources,
    )


def score_mcq_test(request: SubmitMcqRequest) -> SubmitMcqResponse:
    answers = {answer.question_id: answer.selected_answer for answer in request.answers}
    results: list[McqResultItem] = []
    score = 0

    for question in request.questions:
        if question.type != "mcq":
            continue
        selected = answers.get(question.id, "")
        correct = question.correct_answer or ""
        is_correct = normalize_answer(selected) == normalize_answer(correct)
        if is_correct:
            score += 1
        results.append(
            McqResultItem(
                question_id=question.id,
                question=question.question,
                selected_answer=selected,
                correct_answer=correct,
                is_correct=is_correct,
                explanation=question.explanation,
            )
        )

    total = len(results)
    percentage = round((score / total) * 100, 2) if total else 0
    return SubmitMcqResponse(score=score, total=total, percentage=percentage, results=results)


async def evaluate_written_test(request: EvaluateWrittenRequest) -> EvaluateWrittenResponse:
    answers = {answer.question_id: answer.answer for answer in request.answers}
    results: list[WrittenEvaluationItem] = []

    for question in request.questions:
        if question.type != "written":
            continue
        student_answer = answers.get(question.id, "")
        document_ids = [source.document_id for source in question.sources if source.document_id]
        context, sources = retrieve_context(question.question, document_ids=document_ids)
        if not context:
            results.append(
                WrittenEvaluationItem(
                    question_id=question.id,
                    question=question.question,
                    score=0,
                    feedback="No matching context was found in the uploaded PDF.",
                    model_answer="Not found in the uploaded PDF.",
                    rubric_breakdown={},
                    sources=[],
                )
            )
            continue

        payload = await GroqClient().chat_json(
            WRITTEN_EVALUATION_PROMPT.format(
                question=question.question,
                student_answer=student_answer,
                context=context,
            ),
            temperature=0.1,
        )
        raw_score = payload.get("score", 0)
        try:
            score = max(0.0, min(10.0, float(raw_score)))
        except (TypeError, ValueError):
            score = 0.0
        results.append(
            WrittenEvaluationItem(
                question_id=question.id,
                question=question.question,
                score=score,
                feedback=str(payload.get("feedback", "")),
                model_answer=str(payload.get("model_answer", question.model_answer or "")),
                rubric_breakdown=payload.get("rubric_breakdown", {}),
                sources=sources[:3],
            )
        )

    total = round(sum(item.score for item in results), 2)
    max_score = len(results) * 10.0
    percentage = round((total / max_score) * 100, 2) if max_score else 0
    return EvaluateWrittenResponse(score=total, max_score=max_score, percentage=percentage, results=results)
