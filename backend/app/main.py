import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers.conversation import router

app = FastAPI(
    title="AI Chat Exporter",
    description="Turns a shared AI chat link into an agent memory transfer PDF.",
    version="1.0.0",
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
