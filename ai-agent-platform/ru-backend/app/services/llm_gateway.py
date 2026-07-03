import httpx
from fastapi import HTTPException, status

from app.config import settings


class LLMGatewayError(Exception):
    pass


async def generate_reply(model_provider: str, system_prompt: str, history: list[dict]) -> str:
    """Calls the EU-hosted LLM gateway, which is the only place that holds
    foreign-provider API keys. history items look like {"role": "user"|"assistant", "content": str}."""
    payload = {
        "provider": model_provider,
        "system": system_prompt,
        "messages": history,
    }
    headers = {"X-Gateway-Secret": settings.gateway_shared_secret}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.eu_gateway_url}/v1/generate",
                json=payload,
                headers=headers,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Не удалось связаться с LLM-шлюзом: {exc}",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM-шлюз вернул ошибку: {response.text}",
        )

    data = response.json()
    return data["content"]
