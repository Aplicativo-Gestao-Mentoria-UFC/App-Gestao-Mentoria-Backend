from core.database import engine, Base


async def create_tables() -> None:
    import models.__all_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tabelas ausentes criadas com segurança")


if __name__ == "__main__":
    import asyncio

    asyncio.run(create_tables())
