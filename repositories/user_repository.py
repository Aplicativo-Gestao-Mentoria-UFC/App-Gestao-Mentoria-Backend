from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.__all_models import User


async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(select(User).filter_by(username=username))
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).filter_by(email=email))
    return result.scalars().first()


async def create_user(
    db: AsyncSession, username: str, email: str, hashed_password: str
):
    user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
