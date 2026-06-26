import logging

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.course_class_model import CourseClassModel
from models.user_model import UserRole

from repositories import course_class_repository, user_repository

from repositories.activity_repository import is_teacher_of_class
from schemas.course_class_schema import (
    CourseClassBase,
    CourseClassRegister,
)

from sqlalchemy.orm import selectinload

from models.course_class_model import (
    CourseClassModel,
    course_class_students,
    course_class_monitors,
)


logger = logging.getLogger(__name__)


async def create(
    db: AsyncSession,
    course_class: CourseClassBase,
    teacher_id: UUID,
):
    course_class_register = CourseClassRegister(
        name=course_class.name,
        discipline=course_class.discipline,
        teacher_id=teacher_id,
    )

    try:
        return await course_class_repository.create(db, course_class_register)

    except Exception:
        logger.exception("Erro ao criar turma")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def get_classes(
    db: AsyncSession,
    teacher_id: UUID,
    course_class_id: Optional[UUID] = None,
    **filters,
):
    if course_class_id is None:
        return await course_class_repository.get_teacher_classes(
            db=db,
            teacher_id=teacher_id,
            **filters,
        )

    course_class = await course_class_repository.get_class_by_id(
        db=db,
        course_class_id=course_class_id,
    )

    if course_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turma não encontrada",
        )

    allowed = await course_class_repository.is_teacher_of_class(
        db=db,
        user_id=teacher_id,
        course_class_id=course_class.id,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar essa turma",
        )

    return course_class


async def get_student_classes(
    db: AsyncSession,
    student_id: UUID,
    course_class_id: Optional[UUID] = None,
    **filters,
):
    if course_class_id is None:
        return await course_class_repository.get_student_classes(
            db=db,
            student_id=student_id,
            **filters,
        )

    course_class = await course_class_repository.get_class_by_id(
        db=db,
        course_class_id=course_class_id,
    )

    if course_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turma não encontrada",
        )

    allowed = await course_class_repository.is_student_of_class(
        db=db,
        user_id=student_id,
        course_class_id=course_class.id,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não é aluno dessa turma",
        )

    return course_class


async def get_monitor_classes(
    db: AsyncSession,
    student_id: UUID,
    course_class_id: Optional[UUID] = None,
    **filters,
):
    if course_class_id is None:
        return await course_class_repository.get_monitor_classes(
            db=db,
            student_id=student_id,
            **filters,
        )

    course_class = await course_class_repository.get_class_by_id(
        db=db,
        course_class_id=course_class_id,
    )

    if course_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Turma não encontrada",
        )

    allowed = await course_class_repository.is_monitor_of_class(
        db=db,
        user_id=student_id,
        course_class_id=course_class.id,
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não é monitor dessa turma",
        )

    return course_class


async def add_monitor(
    course_class,
    monitor_email: str,
    db: AsyncSession,
):
    monitor = await user_repository.get_user_by_email(db, email=monitor_email)

    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    if monitor.role != UserRole.student.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas estudantes podem ser monitores",
        )

    already_monitor = await course_class_repository.is_monitor_of_class(
        db=db,
        user_id=monitor.id,
        course_class_id=course_class.id,
    )

    if already_monitor:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse aluno já é monitor da turma",
        )

    try:
        return await course_class_repository.add_monitor(
            db=db,
            course_class=course_class,
            new_monitor=monitor,
        )

    except Exception:
        logger.exception("Erro ao adicionar monitor na turma")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def add_student(
    course_class,
    student_email: str,
    db: AsyncSession,
):
    student = await user_repository.get_user_by_email(db, email=student_email)

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    if student.role != UserRole.student.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Apenas estudantes podem ser adicionados na turma",
        )

    already_student = await course_class_repository.is_student_of_class(
        db=db,
        user_id=student.id,
        course_class_id=course_class.id,
    )

    if already_student:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse aluno já foi adicionado na turma",
        )

    try:
        return await course_class_repository.add_student(
            db=db,
            course_class=course_class,
            new_student=student,
        )

    except Exception:
        logger.exception("Erro ao adicionar aluno na turma")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def remove_monitor(
    course_class,
    monitor_id: UUID,
    db: AsyncSession,
):
    monitor = await user_repository.get_user_by_id(db, monitor_id)

    if monitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    is_monitor = await course_class_repository.is_monitor_of_class(
        db=db,
        user_id=monitor.id,
        course_class_id=course_class.id,
    )

    if not is_monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O monitor não faz parte dessa turma",
        )

    try:
        return await course_class_repository.remove_monitor(
            db=db,
            course_class=course_class,
            monitor=monitor,
        )

    except Exception:
        logger.exception("Erro ao remover monitor da turma")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def remove_student(
    course_class,
    student_id: UUID,
    db: AsyncSession,
):
    student = await user_repository.get_user_by_id(db, student_id)

    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )

    is_student = await course_class_repository.is_student_of_class(
        db=db,
        user_id=student.id,
        course_class_id=course_class.id,
    )

    if not is_student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="O aluno não faz parte dessa turma",
        )

    try:
        return await course_class_repository.remove_student(
            db=db,
            course_class=course_class,
            student=student,
        )

    except Exception:
        logger.exception("Erro ao remover aluno da turma")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )
    
async def get_class_by_id(
    db: AsyncSession,
    course_class_id: UUID,
):
    query = (
        select(CourseClassModel)
        .options(
            selectinload(CourseClassModel.activities),
            selectinload(CourseClassModel.monitor),
            selectinload(CourseClassModel.students),
        )
        .where(CourseClassModel.id == course_class_id)
    )

    result = await db.execute(query)

    return result.scalars().first()

    async def is_teacher_of_class(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
        query = (
            select(CourseClassModel.id).where(
                CourseClassModel.id == course_class_id,
                CourseClassModel.teacher_id == user_id,
            )
        )
    

    result = await db.execute(query)

    return result.scalar_one_or_none() is not None


async def is_monitor_of_class(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
    query = select(course_class_monitors.c.course_class_id).where(
        course_class_monitors.c.course_class_id == course_class_id,
        course_class_monitors.c.monitor_id == user_id,
    )

    result = await db.execute(query)

    return result.scalar_one_or_none() is not None


async def is_student_of_class(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
    query = select(course_class_students.c.course_class_id).where(
        course_class_students.c.course_class_id == course_class_id,
        course_class_students.c.student_id == user_id,
    )

    result = await db.execute(query)

    return result.scalar_one_or_none() is not None


async def has_class_write_permission(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
    is_teacher = await is_teacher_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    if is_teacher:
        return True

    is_monitor = await is_monitor_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    return is_monitor


async def has_class_read_permission(
    db: AsyncSession,
    user_id: UUID,
    course_class_id: UUID,
) -> bool:
    is_teacher = await is_teacher_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    if is_teacher:
        return True

    is_monitor = await is_monitor_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    if is_monitor:
        return True

    is_student = await is_student_of_class(
        db=db,
        user_id=user_id,
        course_class_id=course_class_id,
    )

    return is_student