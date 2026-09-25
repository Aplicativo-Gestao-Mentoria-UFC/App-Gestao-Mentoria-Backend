import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.user_model import UserRole
from repositories import course_class_repository, user_repository
from schemas.course_class_schema import CourseClassBase, CourseClassRegister

logger = logging.getLogger(__name__)


async def create(db: AsyncSession, course_class: CourseClassBase, teacher_id: UUID):
    try:
        return await course_class_repository.create(
            db,
            CourseClassRegister(
                name=course_class.name,
                discipline=course_class.discipline,
                teacher_id=teacher_id,
            ),
        )
    except Exception:
        logger.exception("Erro ao criar turma")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


async def get_classes(db: AsyncSession, teacher_id: UUID, course_class_id: UUID | None = None, **filters):
    if course_class_id is None:
        return await course_class_repository.get_teacher_classes(db, teacher_id, **filters)
    course_class = await course_class_repository.get_class_by_id(db, course_class_id)
    if course_class is None:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    if course_class.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Você não tem permissão para acessar essa turma")
    return course_class


async def get_student_classes(db: AsyncSession, student_id: UUID, course_class_id: UUID | None = None, **filters):
    if course_class_id is None:
        return await course_class_repository.get_student_classes(db, student_id, **filters)
    course_class = await course_class_repository.get_class_by_id(db, course_class_id)
    if course_class is None:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    if not await course_class_repository.is_student_of_class(db, student_id, course_class_id):
        raise HTTPException(status_code=403, detail="Você não é aluno dessa turma")
    return course_class


async def get_monitor_classes(db: AsyncSession, student_id: UUID, course_class_id: UUID | None = None, **filters):
    if course_class_id is None:
        return await course_class_repository.get_monitor_classes(db, student_id, **filters)
    course_class = await course_class_repository.get_class_by_id(db, course_class_id)
    if course_class is None:
        raise HTTPException(status_code=404, detail="Turma não encontrada")
    if not await course_class_repository.is_monitor_of_class(db, student_id, course_class_id):
        raise HTTPException(status_code=403, detail="Você não é monitor dessa turma")
    return course_class


async def add_monitor(course_class, monitor_email: str, db: AsyncSession):
    monitor = await user_repository.get_user_by_email(db, monitor_email.strip().lower())
    if monitor is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if monitor.role != UserRole.student.value:
        raise HTTPException(status_code=400, detail="Apenas estudantes podem ser monitores")
    if await course_class_repository.is_monitor_of_class(db, monitor.id, course_class.id):
        raise HTTPException(status_code=409, detail="Esse aluno já é monitor da turma")
    return await course_class_repository.add_monitor(db, course_class, monitor)


async def add_student(course_class, student_email: str, db: AsyncSession):
    student = await user_repository.get_user_by_email(db, student_email.strip().lower())
    if student is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if student.role != UserRole.student.value:
        raise HTTPException(status_code=400, detail="Apenas estudantes podem ser adicionados na turma")
    if await course_class_repository.is_student_of_class(db, student.id, course_class.id):
        raise HTTPException(status_code=409, detail="Esse aluno já foi adicionado na turma")
    return await course_class_repository.add_student(db, course_class, student)


async def remove_monitor(course_class, monitor_id: UUID, db: AsyncSession):
    monitor = await user_repository.get_user_by_id(db, monitor_id)
    if monitor is None or not await course_class_repository.is_monitor_of_class(db, monitor_id, course_class.id):
        raise HTTPException(status_code=404, detail="O monitor não faz parte dessa turma")
    return await course_class_repository.remove_monitor(db, course_class, monitor)


async def remove_student(course_class, student_id: UUID, db: AsyncSession):
    student = await user_repository.get_user_by_id(db, student_id)
    if student is None or not await course_class_repository.is_student_of_class(db, student_id, course_class.id):
        raise HTTPException(status_code=404, detail="O aluno não faz parte dessa turma")
    return await course_class_repository.remove_student(db, course_class, student)
