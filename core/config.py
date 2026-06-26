from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_STR: str
    CORS_ORIGINS: str

    DB_URL: str

    #JWT Settings
    JWT_SECRET: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    #Email Settings
    MAIL_HOST: str
    MAIL_PORT: int = 587
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_FROM_NAME: str = "Sistema de Monitoria"
    

    FRONTEND_URL: str = "http://localhost:3000"

    LOGO_URL: str = "https://cdn-icons-png.flaticon.com/512/11305/11305888.png"

    class Config:
        env_file = ".env"
        class_sensitive = True


settings = Settings()
