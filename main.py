from fastapi import FastAPI
from routes.auth_routes import router
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

app = FastAPI()

app.include_router(router, tags=["auth"])

origins = [settings.CORS_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow__credentials=True,
    allow_methods=["*"],
    allow_credentials=["*"],
)
