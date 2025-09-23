from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_STR: str
    
    DB_URL: str

    JWT_SECRET: str
    ALGORITHM: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int

    class Config:
        env_file = ".env"
        class_sensitive = True

settings = Settings()