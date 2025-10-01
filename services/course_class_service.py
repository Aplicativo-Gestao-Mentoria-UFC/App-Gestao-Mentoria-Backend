from typing import Optional

from fastapi import HTTPException, status
from repositories import course_class_repository, user_repository
from schemas.course_class_schema import CourseClassBase, CourseClassRegister
from sqlalchemy.ext.asyncio import AsyncSession


async def create(db: AsyncSession, course_class: CourseClassBase, teacher_id: str):
    course_class_register = CourseClassRegister(
        name=course_class.name,
        discipline=course_class.discipline,
        teacher_id=teacher_id,
    )

    try:
        return await course_class_repository.create(db, course_class_register)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def get_classes(
    db: AsyncSession, teacher_id: str, course_class_id: Optional[str] = None, **filters
):
    try:
        if course_class_id is None:
            return await course_class_repository.get_teacher_classes(
                db, teacher_id, **filters
            )
        else:
            course_class = await course_class_repository.get_teacher_class_by_id(
                db, teacher_id, course_class_id
            )

            if course_class is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada"
                )

            return course_class

    except Exception as e:
        raise e


async def add_monitor(
    course_class_id: str, monitor_email: str, db: AsyncSession, teacher_id: str
):
    course_class = await course_class_repository.get_teacher_class_by_id(
        db, teacher_id, course_class_id
    )

    if not course_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Essa turma não existe"
        )

    if course_class.teacher_id != teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não é o responsável por essa turma",
        )

    monitor = await user_repository.get_user_by_email(db, email=monitor_email)
    if not monitor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não existe nenhum estudante com esse email",
        )

    if monitor in course_class.monitor:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse aluno já é monitor da turma",
        )

    try:
        return await course_class_repository.add_monitor(db, course_class, monitor)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )


async def add_student(
    course_class_id: str, student_email: str, db: AsyncSession, teacher_id: str
):
    course_class = await course_class_repository.get_teacher_class_by_id(
        db, teacher_id, course_class_id
    )

    if not course_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Essa turma não existe"
        )

    if course_class.teacher_id != teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não é o responsável por essa turma",
        )

    student = await user_repository.get_user_by_email(db, email=student_email)

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não existe nenhum estudante com esse email",
        )

    if student in course_class.students:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Esse aluno já foi adicionado na turma",
        )

    try:
        return await course_class_repository.add_student(db, course_class, student)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor",
        )
