from core.database import engine, Base


async def create_tables() -> None:
    from models.__all_models import UserModel

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Tabelas criadas")


if __name__ == "__main__":
    import asyncio

    asyncio.run(create_tables())
