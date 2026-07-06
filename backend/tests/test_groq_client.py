from __future__ import annotations

import asyncio


def test_chat_json_retries_and_validates_schema(temp_app_settings, monkeypatch) -> None:
    from app.models import LLMAnswerPayload
    from app.services.groq_client import GroqClient

    calls: list[str] = []
    client = GroqClient()

    async def fake_chat(prompt: str, *, temperature: float = 0.2) -> str:
        calls.append(prompt)
        if len(calls) == 1:
            return '{"not_answer": "missing required field"}'
        return '{"answer": "Retry fixed the payload."}'

    monkeypatch.setattr(client, "chat", fake_chat)

    payload = asyncio.run(client.chat_json("Return an answer.", schema_model=LLMAnswerPayload, max_retries=1))

    assert payload["answer"] == "Retry fixed the payload."
    assert len(calls) == 2
    assert "failed JSON/schema validation" in calls[1]
