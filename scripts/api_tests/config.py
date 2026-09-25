from __future__ import annotations

import os


BASE_URL = os.getenv("API_TEST_BASE_URL", "http://localhost:8000").rstrip("/")
REQUEST_TIMEOUT = float(os.getenv("API_TEST_TIMEOUT", "20"))

STUDENT_EMAIL = os.getenv("API_TEST_STUDENT_EMAIL", "pedroerykles@gmail.com")
STUDENT_USERNAME = os.getenv("API_TEST_STUDENT_USERNAME", "aluno_pedro")
STUDENT_PASSWORD = os.getenv("API_TEST_STUDENT_PASSWORD", "Aluno@12345")
STUDENT_NEW_PASSWORD = os.getenv("API_TEST_STUDENT_NEW_PASSWORD", "AlunoNova@12345")

PROFESSOR_INSTITUTIONAL_EMAIL = os.getenv(
    "API_TEST_PROFESSOR_INSTITUTIONAL_EMAIL",
    "pedroerykles@alu.ufc.br",
)
PROFESSOR_ACCOUNT_EMAIL = os.getenv(
    "API_TEST_PROFESSOR_ACCOUNT_EMAIL",
    PROFESSOR_INSTITUTIONAL_EMAIL,
)
PROFESSOR_USERNAME = os.getenv("API_TEST_PROFESSOR_USERNAME", "prof_pedro")
PROFESSOR_PASSWORD = os.getenv("API_TEST_PROFESSOR_PASSWORD", "Professor@12345")

CLASS_NAME = os.getenv("API_TEST_CLASS_NAME", "Turma de Teste Automatizado")
CLASS_DISCIPLINE = os.getenv("API_TEST_CLASS_DISCIPLINE", "Engenharia de Software")

TEACHER_ACTIVITY_TITLE = os.getenv(
    "API_TEST_TEACHER_ACTIVITY_TITLE", "Material inicial do professor"
)
MONITOR_ACTIVITY_TITLE = os.getenv(
    "API_TEST_MONITOR_ACTIVITY_TITLE", "Material enviado pelo monitor"
)
TEST_FILE_URL = os.getenv(
    "API_TEST_FILE_URL", "https://example.com/materiais/atividade-teste.pdf"
)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


REQUIRE_MAILPIT = _env_bool("API_TEST_REQUIRE_MAILPIT", True)
MAILPIT_WEB_URL = os.getenv("API_TEST_MAILPIT_URL", "http://localhost:8025").rstrip("/")
MAILPIT_SMTP_HOST = os.getenv("API_TEST_SMTP_HOST", "localhost")
MAILPIT_SMTP_PORT = int(os.getenv("API_TEST_SMTP_PORT", "1025"))
