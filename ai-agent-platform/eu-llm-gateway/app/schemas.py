from typing import Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class GenerateRequest(BaseModel):
    provider: Literal["claude", "gpt", "gemini"]
    system: str
    messages: list[ChatMessage]


class GenerateResponse(BaseModel):
    content: str
