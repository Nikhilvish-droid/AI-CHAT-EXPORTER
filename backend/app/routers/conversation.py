from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from urllib.parse import urlparse
import re

from backend.app.services.chatgpt_scraper.chatgptscraper import load_chatgpt_chat
from backend.app.services.gemini_scraper.geminiscraper import load_gemini_chat
from backend.app.services.claude_scraper.claudescraper import load_claude_chat

from backend.app.services import assets as assetlib
from backend.app.services.codeblocks import extract_code_blocks
from backend.app.services.chunks import create_chunks
from backend.app.services.embedding import create_embeddings
from backend.app.services.chroma import add_chunks_to_chroma
from backend.app.services.retrieval import retrieve_data
from backend.app.services.llm import openai_llm
from backend.app.services.pdfgenerator import generate_pdf


def safe_segment(value, fallback="memory_export"):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._-")

    return cleaned[:80] or fallback


router = APIRouter()

output_dir = Path(__file__).parent.parent / "output"

ALLOWED_HOSTS = {
    "chatgpt.com": ("chatgpt", load_chatgpt_chat),
    "chat.openai.com": ("chatgpt", load_chatgpt_chat),
    "gemini.google.com": ("gemini", load_gemini_chat),
    "share.gemini.google": ("gemini", load_gemini_chat),
    "g.co": ("gemini", load_gemini_chat),
    "claude.ai": ("claude", load_claude_chat),
}


def pick_scraper(url):
    try:
        parsed = urlparse(url)
    except ValueError:
        return None, None, "url could not be parsed"

    if parsed.scheme not in ("http", "https"):
        return None, None, "url must start with http:// or https://"

    host = (parsed.hostname or "").lower().lstrip(".")

    if not host:
        return None, None, "url has no host"

    for allowed, (name, loader) in ALLOWED_HOSTS.items():
        if host == allowed or host.endswith("." + allowed):
            return name, loader, None

    return None, None, (
        "Unsupported link. Provide a share URL from "
        "chatgpt.com, gemini.google.com or claude.ai."
    )


def stage(description, func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{description} failed: {e}")


@router.post("/submit-link")
def submit_link(url: str):
    if not isinstance(url, str) or not url.strip():
        raise HTTPException(status_code=422, detail="url is required")

    url = url.strip()
    platform, loader, problem = pick_scraper(url)

    if problem:
        raise HTTPException(status_code=422, detail=problem)

    response = stage("Scraping the conversation", loader, url)

    if not isinstance(response, dict) or not response.get("ok"):
        message = (response or {}).get("message") if isinstance(response, dict) else None

        raise HTTPException(
            status_code=502,
            detail=message or f"{platform}: could not read the conversation",
        )

    chat_data = response.get("data")

    if not isinstance(chat_data, dict) or not chat_data.get("messages"):
        raise HTTPException(
            status_code=502,
            detail=f"{platform}: conversation contained no readable messages",
        )

    conversation_id = chat_data.get("conversation_id") or safe_segment(chat_data.get("title"), "run")
    platform_name = chat_data.get("platform") or platform
    manifest = stage("Collecting attachments", assetlib.manifest, chat_data["messages"])
    code_blocks = stage("Extracting code blocks", extract_code_blocks, chat_data["messages"])

    chunks = stage("Chunking the conversation", create_chunks, chat_data)

    if not chunks.get("ok"):
        raise HTTPException(status_code=422, detail=chunks.get("message") or "Chunking failed")

    embeddings = stage("Embedding the conversation", create_embeddings, chunks["chunks"])

    if not embeddings.get("ok"):
        raise HTTPException(status_code=500, detail=embeddings.get("message") or "Embedding failed")

    stored = stage("Storing vectors", add_chunks_to_chroma, embeddings["data"])

    if not stored.get("ok"):
        raise HTTPException(status_code=500, detail=stored.get("message") or "Vector store failed")

    retrieval_data = stage(
        "Retrieving context",
        retrieve_data,
        stored.get("conversation_id"),
        embeddings.get("docs_embed"),
    )

    if not retrieval_data:
        raise HTTPException(
            status_code=500,
            detail="Retrieval returned no context for this conversation",
        )

    try:
        final_data = openai_llm(retrieval_data)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Document generation failed: {e}")

    if not isinstance(final_data, dict):
        raise HTTPException(
            status_code=502,
            detail="Document generation returned an unexpected format",
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{safe_segment(conversation_id, 'memory_export')}.pdf"

    stage(
        "PDF generation",
        generate_pdf,
        title=chat_data.get("title"),
        source_url=chat_data.get("source_url") or url,
        platform=platform_name,
        final_data=final_data,
        output_file=output_file,
        assets=manifest,
        code_blocks=code_blocks,
    )

    if not output_file.exists():
        raise HTTPException(status_code=500, detail="PDF was not written")

    return FileResponse(
        path=output_file,
        media_type="application/pdf",
        filename=f"{safe_segment(chat_data.get('title'), 'memory_export')}.pdf",
        headers={
            "Access-Control-Expose-Headers": (
                "X-Conversation-Id, X-Platform, X-Images-Embedded, "
                "X-Files-Missing, X-Code-Blocks, X-Messages-Skipped"
            ),
            "X-Conversation-Id": str(conversation_id),
            "X-Platform": str(platform_name),
            "X-Images-Embedded": str(len(manifest["embedded"])),
            "X-Files-Missing": str(len(manifest["missing"])),
            "X-Code-Blocks": str(len(code_blocks)),
            "X-Messages-Skipped": str(len(chunks.get("messages_without_chunk") or [])),
        },
    )
