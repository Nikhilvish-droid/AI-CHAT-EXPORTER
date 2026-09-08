from fastapi import APIRouter, UploadFile, File, staticfiles
from fastapi.responses import JSONResponse
from pathlib import Path
from fastapi.responses import FileResponse
# from app.services.fetcher import html_fetcher
from app.services.scraper import chat_scraper
from app.services.chunks import create_chunks
from app.services.embedding import create_embeddings
from app.services.chroma import add_chunks_to_chroma
from app.services.retrieval import retrieve_data
from app.services.llm import openai_llm
from app.services.pdfgenerator import generate_pdf


router = APIRouter()
output_file = Path(__file__).parent.parent / "output" / "memory_export.pdf"


@router.post("/submit-link")
def submit_link(url: str):

    response = chat_scraper(url)

    if not response.get("ok"):
        return response.get("message")

    chat_data = response.get("data")
    
    # use for pdf making these three line
    title = chat_data.get("title")
    platform = chat_data.get("platform")
    chat_url = chat_data.get("source_url")

    chunks = create_chunks(chat_data)
    chunk_data = chunks.get("chunks")

    embeddings = create_embeddings(chunk_data)
    embedd_data = embeddings.get("data")

    # store in chroma db
    chroma_msg = add_chunks_to_chroma(embedd_data)
    conversation_id = chroma_msg.get("conversation_id")
    
    retrieval_data = retrieve_data(conversation_id)


    final_data = openai_llm(retrieval_data)

    result = generate_pdf(title=title, source_url=chat_url, platform = platform, final_data=final_data)

    return FileResponse(
            path=output_file, 
            media_type="application/pdf",
            filename="memory_export.pdf",
            headers={
                "status_code": 201,
                "message":"pdf created succesfully"
            }
        )






