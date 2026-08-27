from fastapi import APIRouter
from app.services.fetcher import html_fetcher

router = APIRouter()

@router.post("/submit-link")
def submit_link(url: str):
    data = html_fetcher(url)

    return data;




