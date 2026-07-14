from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .database import Base, engine
from .routers import chat, hcps, interactions, voice

settings = get_settings()
app = FastAPI(title="AI-First CRM — HCP Module", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(interactions.router)
app.include_router(hcps.router)
app.include_router(chat.router)
app.include_router(voice.router)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok", "service": "hcp-crm-api"}
