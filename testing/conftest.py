import pytest
import pytest_asyncio

from services import confirmation_service

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from main import app
from core import deps
from testing.fake.fake_email_service import FakeEmailService


@pytest.fixture
def fake_email_service() -> FakeEmailService: 
    return FakeEmailService()

@pytest_asyncio.fixture
async def client(
    test_db_session: AsyncSession,
    fake_email_service: FakeEmailService,
    monkeypatch: pytest.MonkeyPatch,
):
    async def override_get_session():
        yield test_db_session

    app.dependency_overrides[deps.get_session] = override_get_session

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(deps.get_session, None)