from fastapi import FastAPI, HTTPException, APIRouter
from app.routers.conversation import router

app = FastAPI()
app.include_router(router)