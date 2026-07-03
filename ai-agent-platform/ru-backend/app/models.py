from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    agents = relationship("Agent", back_populates="owner", cascade="all, delete-orphan")


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    personality = Column(Text, nullable=False)
    goal = Column(Text, nullable=False)
    restrictions = Column(Text, default="")
    greeting = Column(String, default="Привет! Чем могу помочь?")
    model_provider = Column(String, default="claude")

    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="agents")
    documents = relationship("KnowledgeDocument", back_populates="agent", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="agent", cascade="all, delete-orphan")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="documents")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)

    document = relationship("KnowledgeDocument", back_populates="chunks")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="messages")
