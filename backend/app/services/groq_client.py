from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import get_settings
from app.prompts import SYSTEM_RAG_RULES


class GroqClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def chat(self, user_prompt: str, *, temperature: float = 0.2) -> str:
        if not self.settings.groq_api_key:
            raise HTTPException(
                status_code=503,
                detail="GROQ_API_KEY is not configured. Add it to .env before using generation endpoints.",
            )

        payload = {
            "model": self.settings.groq_model,
            "messages": [
                {"role": "system", "content": SYSTEM_RAG_RULES},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        data = response.json()
        return data["choices"][0]["message"]["content"]

    async def chat_json(self, user_prompt: str, *, temperature: float = 0.2) -> dict[str, Any]:
        content = await self.chat(user_prompt, temperature=temperature)
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    pass
        raise HTTPException(status_code=502, detail="The LLM returned invalid JSON.")
