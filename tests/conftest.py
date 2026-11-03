import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.core.config import settings

# Force test environment for tests
settings.ENVIRONMENT = "test"
settings.USE_MOCK_DB = True

from backend.core.security import create_access_token
from backend.db.mongodb import close_mongodb_connection, connect_to_mongodb
from backend.db.redis import close_redis_connection, connect_to_redis
from backend.main import _seed_initial_data, app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_test_backend():
    db = await connect_to_mongodb()
    await connect_to_redis()
    await _seed_initial_data(db)
    yield
    await close_mongodb_connection()
    await close_redis_connection()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def admin_token():
    return create_access_token({"sub": "user_admin_001", "email": "admin@sentinelops.local", "role": "admin"})


@pytest.fixture
def operator_token():
    return create_access_token({"sub": "user_operator_001", "email": "operator@sentinelops.local", "role": "operator"})


@pytest.fixture
def viewer_token():
    return create_access_token({"sub": "user_viewer_001", "email": "viewer@sentinelops.local", "role": "viewer"})
