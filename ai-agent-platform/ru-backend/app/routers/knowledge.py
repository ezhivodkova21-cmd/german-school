from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.routers.agents import _get_owned_agent
from app.services.retrieval import split_into_chunks

router = APIRouter(prefix="/agents/{agent_id}/knowledge", tags=["knowledge"])


@router.post("", response_model=schemas.KnowledgeDocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    agent_id: int,
    payload: schemas.KnowledgeDocumentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, user)

    document = models.KnowledgeDocument(agent_id=agent.id, title=payload.title, content=payload.content)
    db.add(document)
    db.flush()

    for chunk_text in split_into_chunks(payload.content):
        db.add(models.KnowledgeChunk(document_id=document.id, agent_id=agent.id, content=chunk_text))

    db.commit()
    db.refresh(document)
    return document


@router.get("", response_model=list[schemas.KnowledgeDocumentOut])
def list_documents(
    agent_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, user)
    return db.query(models.KnowledgeDocument).filter(models.KnowledgeDocument.agent_id == agent.id).all()


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    agent_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, user)
    document = (
        db.query(models.KnowledgeDocument)
        .filter(models.KnowledgeDocument.id == document_id, models.KnowledgeDocument.agent_id == agent.id)
        .first()
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

    db.delete(document)
    db.commit()
