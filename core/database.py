from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession

from core.config import settings

engine: AsyncEngine = create_async_engine(settings.DB_URL)

Session: AsyncSession = sessionmaker(
    autoflush=False, expire_on_commit=False, class_=AsyncSession, bind=engine
)

Base = declarative_base()
