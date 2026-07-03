from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.routers.agents import _get_owned_agent
from app.services.llm_gateway import generate_reply
from app.services.prompt_builder import build_system_prompt
from app.services.retrieval import retrieve_relevant_chunks

router = APIRouter(prefix="/agents/{agent_id}", tags=["chat"])

HISTORY_LIMIT = 20


@router.get("/messages", response_model=list[schemas.MessageOut])
def get_messages(agent_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    agent = _get_owned_agent(db, agent_id, user)
    return (
        db.query(models.Message)
        .filter(models.Message.agent_id == agent.id, models.Message.user_id == user.id)
        .order_by(models.Message.created_at.asc())
        .all()
    )


@router.post("/chat", response_model=schemas.ChatResponse)
async def chat(
    agent_id: int,
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, user)

    past_messages = (
        db.query(models.Message)
        .filter(models.Message.agent_id == agent.id, models.Message.user_id == user.id)
        .order_by(models.Message.created_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    past_messages.reverse()

    relevant_chunks = retrieve_relevant_chunks(db, agent.id, payload.message)
    knowledge_context = "\n---\n".join(relevant_chunks)
    system_prompt = build_system_prompt(agent, knowledge_context)

    history = [{"role": m.role, "content": m.content} for m in past_messages]
    history.append({"role": "user", "content": payload.message})

    reply_text = await generate_reply(agent.model_provider, system_prompt, history)

    db.add(models.Message(agent_id=agent.id, user_id=user.id, role="user", content=payload.message))
    db.add(models.Message(agent_id=agent.id, user_id=user.id, role="assistant", content=reply_text))
    db.commit()

    return schemas.ChatResponse(reply=reply_text)
