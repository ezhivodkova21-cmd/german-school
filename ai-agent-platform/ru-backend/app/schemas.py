from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=200)
    personality: str = Field(min_length=1, max_length=500)
    goal: str = Field(min_length=1, max_length=500)
    restrictions: str = Field(default="", max_length=500)
    greeting: str = Field(default="Привет! Чем могу помочь?", max_length=200)
    model_provider: Literal["claude", "gpt", "gemini"] = "claude"


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    role: Optional[str] = Field(default=None, max_length=200)
    personality: Optional[str] = Field(default=None, max_length=500)
    goal: Optional[str] = Field(default=None, max_length=500)
    restrictions: Optional[str] = Field(default=None, max_length=500)
    greeting: Optional[str] = Field(default=None, max_length=200)
    model_provider: Optional[Literal["claude", "gpt", "gemini"]] = None


class AgentOut(BaseModel):
    id: int
    name: str
    role: str
    personality: str
    goal: str
    restrictions: str
    greeting: str
    model_provider: str
    created_at: datetime

    class Config:
        from_attributes = True


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=50_000)


class KnowledgeDocumentOut(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    reply: str
