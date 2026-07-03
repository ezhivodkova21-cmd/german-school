from fastapi import FastAPI, Header, HTTPException, status

from app.config import settings
from app.providers import generate
from app.schemas import GenerateRequest, GenerateResponse

app = FastAPI(title="AI Agent Platform — EU LLM gateway", version="0.1.0")


def _check_secret(x_gateway_secret: str | None) -> None:
    if x_gateway_secret != settings.gateway_shared_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Неверный shared secret")


@app.post("/v1/generate", response_model=GenerateResponse)
async def generate_endpoint(
    payload: GenerateRequest,
    x_gateway_secret: str | None = Header(default=None),
):
    _check_secret(x_gateway_secret)
    content = await generate(payload.provider, payload.system, payload.messages)
    return GenerateResponse(content=content)


@app.get("/health")
def health():
    return {"status": "ok"}
