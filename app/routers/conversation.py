from fastapi import APIRouter
from fastapi.responses import JSONResponse
# from app.services.fetcher import html_fetcher
from app.services.scraper import chat_scraper
from app.services.chunks import create_chunks
from app.services.embedding import create_embeddings
from app.services.chroma import add_chunks_to_chroma
from app.services.retrieval import retrieve_data

router = APIRouter()

@router.post("/submit-link")
def submit_link(url: str): 

    response = chat_scraper(url)

    if not response.get("ok"):
        return response.get("message")

    chat_data = response.get("data")

    chunks = create_chunks(chat_data)
    chunk_data = chunks.get("chunks")

    embeddings = create_embeddings(chunk_data)
    embedd_data = embeddings.get("data")

    # store in chroma db
    chroma_msg = add_chunks_to_chroma(embedd_data)
    conversation_id = chroma_msg.get("conversation_id")
    
    retrieval_data = retrieve_data(conversation_id)

    return JSONResponse(
        status_code=201,
        content=retrieval_data
    )






