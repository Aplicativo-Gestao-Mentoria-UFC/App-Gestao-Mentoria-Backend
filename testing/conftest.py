import pytest

from testing.fake.fake_email_service import FakeEmailService


@pytest.fixture
def fake_email_service() -> FakeEmailService:
    return FakeEmailService()
