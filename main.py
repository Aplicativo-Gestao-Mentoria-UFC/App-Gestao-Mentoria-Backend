from fastapi import FastAPI
from routes import auth_routes, teacher_routes
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings

app = FastAPI()

app.include_router(auth_routes.router, tags=["auth"])
app.include_router(teacher_routes.router, tags=["teacher"])

origins = [settings.CORS_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
