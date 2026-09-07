import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_urls_are_available():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in ("/health", "/api/health"):
            response = await client.get(path)
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
