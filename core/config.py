from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    API_STR: str = ""
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    DB_URL: str = "postgresql+asyncpg://mentoria:mentoria@localhost:5432/mentoria"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    PROFESSOR_SIGNUP_CODE_EXPIRE_MINUTES: int = 30
    PROFESSOR_SIGNUP_TOKEN_EXPIRE_MINUTES: int = 30
    PROFESSOR_SIGNUP_MAX_ATTEMPTS: int = 5

    # Domínios aceitos no fluxo de cadastro de professor.
    # Separe múltiplos domínios por vírgula, por exemplo: ufc.br,alu.ufc.br
    INSTITUTIONAL_EMAIL_DOMAINS: str = "ufc.br"

    # Email / SMTP
    MAIL_HOST: str = "localhost"
    MAIL_PORT: int = 1025
    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: str | None = None
    MAIL_FROM: str = "no-reply@mentoria.local"
    MAIL_FROM_NAME: str = "Sistema de Monitoria"
    MAIL_START_TLS: bool = False
    MAIL_VALIDATE_CERTS: bool = True

    FRONTEND_URL: str = "http://localhost:3000"
    LOGO_URL: str = "https://cdn-icons-png.flaticon.com/512/11305/11305888.png"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def institutional_email_domains(self) -> set[str]:
        return {
            domain.strip().lower().lstrip("@")
            for domain in self.INSTITUTIONAL_EMAIL_DOMAINS.split(",")
            if domain.strip()
        }


settings = Settings()
