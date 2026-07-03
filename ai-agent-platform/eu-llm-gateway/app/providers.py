import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.schemas import ChatMessage

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


async def call_claude(system: str, messages: list[ChatMessage]) -> str:
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ANTHROPIC_API_KEY не настроен на eu-llm-gateway",
        )

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.anthropic_default_model,
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": m.role, "content": m.content} for m in messages],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Anthropic API error: {response.text}",
        )

    data = response.json()
    return "".join(block["text"] for block in data["content"] if block["type"] == "text")


async def generate(provider: str, system: str, messages: list[ChatMessage]) -> str:
    if provider == "claude":
        return await call_claude(system, messages)

    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Провайдер '{provider}' пока не подключён к eu-llm-gateway",
    )
