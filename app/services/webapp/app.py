from fastapi import FastAPI
from app.services.webapp.handler import router

app = FastAPI()
app.include_router(router)