from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_STR: str
    DB_URL: str
    ALGORITHM: str

    class Config:
        env_file = ".env"
        class_sensitive = True

settings = Settings()