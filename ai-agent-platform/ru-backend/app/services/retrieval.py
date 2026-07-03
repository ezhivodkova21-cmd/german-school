import re

from sqlalchemy.orm import Session

from app import models

CHUNK_SIZE = 800
TOP_K = 3


def split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buffer = ""

    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 1 <= chunk_size:
            buffer = f"{buffer}\n{paragraph}".strip()
        else:
            if buffer:
                chunks.append(buffer)
            buffer = paragraph

    if buffer:
        chunks.append(buffer)

    return chunks or [text.strip()]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Zа-яА-ЯёЁ0-9]+", text.lower()))


def retrieve_relevant_chunks(db: Session, agent_id: int, query: str, top_k: int = TOP_K) -> list[str]:
    """Naive keyword-overlap retrieval. Good enough for MVP; swap for an
    embeddings/vector-store lookup once the knowledge base grows."""
    chunks = db.query(models.KnowledgeChunk).filter(models.KnowledgeChunk.agent_id == agent_id).all()
    if not chunks:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored = []
    for chunk in chunks:
        overlap = len(query_tokens & _tokenize(chunk.content))
        if overlap > 0:
            scored.append((overlap, chunk.content))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [content for _, content in scored[:top_k]]
