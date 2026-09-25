import pytest

from core.config import settings
from models.user_model import UserRole
from schemas.user_schema import validate_strong_password, validate_teacher_institutional_email


def test_strong_password_accepts_valid_password():
    assert validate_strong_password("Senha@123") == "Senha@123"


def test_strong_password_rejects_weak_password():
    with pytest.raises(ValueError):
        validate_strong_password("12345678")


def test_institutional_domain_is_configurable(monkeypatch):
    monkeypatch.setattr(settings, "INSTITUTIONAL_EMAIL_DOMAINS", "alu.ufc.br")
    assert (
        validate_teacher_institutional_email("teste@alu.ufc.br", UserRole.teacher)
        == "teste@alu.ufc.br"
    )


def test_teacher_rejects_domain_outside_env(monkeypatch):
    monkeypatch.setattr(settings, "INSTITUTIONAL_EMAIL_DOMAINS", "alu.ufc.br")
    with pytest.raises(ValueError):
        validate_teacher_institutional_email("teste@ufc.br", UserRole.teacher)
