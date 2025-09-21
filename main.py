from fastapi import FastAPI
from core.config import settings
from core.database import engine

app = FastAPI()

@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(settings.DBBaseModel.metadata.create_all)