from fastapi import APIRouter
from fastapi.responses import JSONResponse
# from app.services.fetcher import html_fetcher
from app.services.scraper import chat_scraper

router = APIRouter()

@router.post("/submit-link")
def submit_link(url: str): 

    response = chat_scraper(url)

    return JSONResponse(
        status_code=201,
        content=response
    )






