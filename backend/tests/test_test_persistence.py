from __future__ import annotations

import asyncio


def test_generated_test_and_result_are_persisted(temp_app_settings, monkeypatch) -> None:
    from app import database
    from app.models import GenerateTestRequest, SaveTestResultRequest, SourceRef, SubmitMcqResponse
    from app.services import test_service

    sources = [
        SourceRef(
            document_id="doc-1",
            file_name="notes.pdf",
            page_number=2,
            chunk_id="chunk-1",
            score=0.2,
        )
    ]

    monkeypatch.setattr(test_service, "retrieve_context", lambda *args, **kwargs: ("PDF context", sources))

    class FakeGroqClient:
        async def chat_json(self, *args, **kwargs):
            return {
                "questions": [
                    {
                        "type": "mcq",
                        "question": "What is tested?",
                        "options": ["A", "B", "C", "D"],
                        "correct_answer": "A",
                        "explanation": "The PDF says A.",
                    }
                ]
            }

    monkeypatch.setattr(test_service, "GroqClient", FakeGroqClient)

    generated = asyncio.run(
        test_service.generate_test(
            GenerateTestRequest(mode="mcq", difficulty="Easy", num_questions=1, topic="sample", document_ids=["doc-1"])
        )
    )

    saved = database.get_generated_test(generated.test_id)
    assert saved is not None
    assert saved["questions"][0]["question"] == "What is tested?"

    result = test_service.save_test_result(
        SaveTestResultRequest(
            test=generated,
            mcq=SubmitMcqResponse(score=1, total=1, percentage=100, results=[]),
            written=None,
        )
    )

    assert result.test.test_id == generated.test_id
    assert result.percentage == 100
    assert test_service.list_saved_results()[0].result_id == result.result_id
