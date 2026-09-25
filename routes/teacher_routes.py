from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core import deps
from models.__all_models import UserRole
from schemas.activity_schema import Activity, ActivityCreate
from schemas.course_class_schema import AddStudentSchema, CourseClass, CourseClassBase, RemoveStudentSchema
from schemas.user_schema import User
from services import activity_service, course_class_service
from services.auth_service import require_role, require_teacher_class

router = APIRouter(prefix="/teacher", dependencies=[Depends(require_role(UserRole.teacher))])


@router.post("/register-class", response_model=CourseClass, summary="Criar turma")
async def register_class(
    course_class: CourseClassBase,
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role(UserRole.teacher)),
):
    return await course_class_service.create(db, course_class, current_user.id)


@router.get("/my-classes", response_model=list[CourseClass], summary="Listar minhas turmas")
async def get_classes(
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role(UserRole.teacher)),
    name: Optional[str] = None,
    discipline: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
):
    return await course_class_service.get_classes(
        db,
        current_user.id,
        name=name,
        discipline=discipline,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/my-classes/{course_class_id}", response_model=CourseClass, summary="Detalhar minha turma")
async def get_teacher_class_by_id(
    course_class_id: UUID,
    db: AsyncSession = Depends(deps.get_session),
    current_user: User = Depends(require_role(UserRole.teacher)),
):
    return await course_class_service.get_classes(db, current_user.id, course_class_id)


@router.put("/my-classes/{course_class_id}/add-monitor", response_model=CourseClass, summary="Adicionar monitor")
async def add_monitor(
    data: AddStudentSchema,
    course_class=Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    return await course_class_service.add_monitor(course_class, str(data.email), db)


@router.patch("/my-classes/{course_class_id}/remove-monitor", response_model=CourseClass, summary="Remover monitor")
async def remove_monitor(
    data: RemoveStudentSchema,
    course_class=Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    return await course_class_service.remove_monitor(
        course_class,
        deps.validate_uuid(data.student_id),
        db,
    )


@router.put("/my-classes/{course_class_id}/add-student", response_model=CourseClass, summary="Adicionar aluno")
async def add_student(
    data: AddStudentSchema,
    course_class=Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    return await course_class_service.add_student(course_class, str(data.email), db)


@router.patch("/my-classes/{course_class_id}/remove-student", response_model=CourseClass, summary="Remover aluno")
async def remove_student(
    data: RemoveStudentSchema,
    course_class=Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    return await course_class_service.remove_student(
        course_class,
        deps.validate_uuid(data.student_id),
        db,
    )


@router.post("/my-classes/{course_class_id}/add-activity", response_model=Activity, summary="Adicionar atividade")
async def add_activity(
    activity: ActivityCreate,
    course_class=Depends(require_teacher_class()),
    db: AsyncSession = Depends(deps.get_session),
):
    return await activity_service.create(db, activity, course_class.id)
