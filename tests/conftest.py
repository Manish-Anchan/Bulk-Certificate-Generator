from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import database
from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.services.storage_service import storage_service


@pytest.fixture(autouse=True)
async def setup_test_environment(tmp_path: Path):
    """Set up isolated file storage and isolated SQLite database for each test."""
    # 1. Configure temporary storage directory
    storage_service.base_dir = tmp_path / "storage"
    storage_service.base_dir.mkdir(parents=True, exist_ok=True)
    settings.STORAGE_DIR = str(storage_service.base_dir)

    # 2. Configure temporary SQLite database file
    db_file = tmp_path / "test_certificates.db"
    test_db_url = f"sqlite+aiosqlite:///{db_file}"
    settings.DATABASE_URL = test_db_url

    test_engine = create_async_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
    )
    test_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Re-bind global database singletons so background tasks and services use the test database
    database.engine = test_engine
    database.AsyncSessionLocal = test_session_maker

    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await test_engine.dispose()


@pytest.fixture
async def test_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session attached to the test database."""
    async with database.AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def client(test_db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous HTTP test client with overridden database dependency."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with database.AsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()
