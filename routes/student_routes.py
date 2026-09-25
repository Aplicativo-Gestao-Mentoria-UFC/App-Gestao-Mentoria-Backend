from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core import deps
from models.__all_models import UserRole
from schemas.course_class_schema import CourseClass
from schemas.user_schema import User
from services import course_class_service
from services.auth_service import require_role, require_student_class

router = APIRouter(prefix="/student", dependencies=[Depends(require_role(UserRole.student))])


@router.get("/my-classes", response_model=list[CourseClass], summary="Listar turmas do aluno")
async def get_classes(
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role(UserRole.student)),
    name: Optional[str] = None,
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
):
    return await course_class_service.get_student_classes(
        db,
        current_user.id,
        name=name,
        discipline=discipline,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/my-classes/{course_class_id}", response_model=CourseClass, summary="Detalhar turma do aluno")
async def get_student_class_by_id(course_class=Depends(require_student_class())):
    return course_class
