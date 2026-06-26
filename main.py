from fastapi import Depends, FastAPI, HTTPException
from routes import auth_routes, teacher_routes, student_routes, monitor_routes, activity_routes
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core import deps

app = FastAPI()

app.include_router(auth_routes.router, tags=["auth"])
app.include_router(teacher_routes.router, tags=["teacher"])
app.include_router(student_routes.router, tags=["student"])
app.include_router(monitor_routes.router, tags=["monitor"])
app.include_router(activity_routes.router, tags=["activities"])

origins = [settings.CORS_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(deps.get_session)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível",
        )
    return {"status": "ok"}
