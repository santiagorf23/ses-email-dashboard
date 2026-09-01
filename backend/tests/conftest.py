import os
import sys

# Set test environment variables BEFORE any app imports
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-1234567890abcdef"
os.environ["ADMIN_PASSWORD"] = "testpassword123"
os.environ["DATABASE_URL"] = "postgresql://user:password@localhost:5432/ses_dashboard_test"
os.environ["ADMIN_USER"] = "admin"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:8080"

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
async def client():
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Return auth headers with a valid token."""
    from routers.auth import create_token
    token = create_token({"sub": "admin"})
    return {"Authorization": f"Bearer {token}"}
