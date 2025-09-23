from core.database import engine, Base

async def create_tables() -> None:
    import models.__all_models
    print("criando")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("amar, amei")

if __name__ == "__main__":
    import asyncio

    asyncio.run(create_tables())