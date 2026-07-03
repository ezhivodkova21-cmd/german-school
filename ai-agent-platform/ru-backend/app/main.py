from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import agents, auth, chat, knowledge

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Agent Platform — RU backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(agents.router)
app.include_router(knowledge.router)
app.include_router(chat.router)


@app.get("/health")
def health():
    return {"status": "ok"}
