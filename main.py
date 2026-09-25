from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core import deps
from core.config import settings
from routes import activity_routes, auth_routes, monitor_routes, student_routes, teacher_routes

TAGS_METADATA = [
    {"name": "auth", "description": "Cadastro, login, confirmação de email e recuperação de senha."},
    {"name": "teacher", "description": "Operações exclusivas do professor."},
    {"name": "student", "description": "Operações de alunos."},
    {"name": "monitor", "description": "Operações de alunos que atuam como monitores."},
    {"name": "activities", "description": "Atividades vinculadas às turmas."},
]

app = FastAPI(
    title="Mentoria API",
    version="1.0.0",
    description=(
        "API do Sistema de Gestão de Mentoria. O fluxo de professor exige validação "
        "prévia de um email institucional configurado via ambiente."
    ),
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(auth_routes.router, tags=["auth"])
app.include_router(teacher_routes.router, tags=["teacher"])
app.include_router(student_routes.router, tags=["student"])
app.include_router(monitor_routes.router, tags=["monitor"])
app.include_router(activity_routes.router, tags=["activities"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"], summary="Health check da API")
async def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["health"], summary="Health check do PostgreSQL")
async def health_db(db: AsyncSession = Depends(deps.get_session)):
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível",
        )
    return {"status": "ok"}
