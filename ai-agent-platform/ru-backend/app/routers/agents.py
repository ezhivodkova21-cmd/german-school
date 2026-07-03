from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user

router = APIRouter(prefix="/agents", tags=["agents"])


def _get_owned_agent(db: Session, agent_id: int, user: models.User) -> models.Agent:
    agent = db.query(models.Agent).filter(models.Agent.id == agent_id).first()
    if agent is None or agent.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Агент не найден")
    return agent


@router.post("", response_model=schemas.AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: schemas.AgentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    agent = models.Agent(owner_id=user.id, **payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("", response_model=list[schemas.AgentOut])
def list_agents(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Agent).filter(models.Agent.owner_id == user.id).all()


@router.get("/{agent_id}", response_model=schemas.AgentOut)
def get_agent(agent_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return _get_owned_agent(db, agent_id, user)


@router.patch("/{agent_id}", response_model=schemas.AgentOut)
def update_agent(
    agent_id: int,
    payload: schemas.AgentUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, field, value)
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    agent = _get_owned_agent(db, agent_id, user)
    db.delete(agent)
    db.commit()
