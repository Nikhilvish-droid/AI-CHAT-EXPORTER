import os
import threading
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from app.routers.conversation import router
from app.services.cleanup import sweep_orphans
from app.services.embedding import get_model


@asynccontextmanager
async def lifespan(app):
    sweep_orphans()

    # Loading torch + the embedding model takes a while on a small instance,
    # so do it in the background instead of on the first /api/analyze call.
    if os.getenv("WARMUP_MODEL", "0").lower() in ("1", "true", "yes"):
        threading.Thread(target=get_model, daemon=True).start()

    yield


app = FastAPI(
    title="AI Chat Exporter",
    description="Turns a shared AI chat link into an agent memory transfer PDF.",
    version="1.0.0",
    lifespan=lifespan,
)

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Conversation-Id",
        "X-Platform",
        "X-Images-Embedded",
        "X-Files-Missing",
        "X-Code-Blocks",
        "X-Messages-Skipped",
        "Content-Disposition",
    ],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
