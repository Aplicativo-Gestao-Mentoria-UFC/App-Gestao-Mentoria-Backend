from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.__all_models import UserModel, UserRole
from schemas.user_schema import User


async def get_user_by_id(db: AsyncSession, id):
    result = await db.execute(select(UserModel).filter_by(id=id))
    return result.scalars().first()


async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(UserModel).filter_by(username=username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(UserModel).filter_by(email=email))
    return result.scalars().first()


async def create_user(
    db: AsyncSession, username: str, email: str, role: UserRole, hashed_password: str
):
    user = UserModel(
        username=username, email=email, role=role, hashed_password=hashed_password
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return User.from_orm(user)
