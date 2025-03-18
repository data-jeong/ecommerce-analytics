import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app
from api.database import Base, get_db
from api.config import Settings

# Test database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture(scope="session")
def test_settings():
    """Create test settings."""
    return Settings(
        OLTP_DATABASE_URL=SQLALCHEMY_DATABASE_URL,
        OLAP_DATABASE_URL=SQLALCHEMY_DATABASE_URL,
        TESTING=True
    )

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()

@pytest.fixture(scope="function")
def client(test_db):
    """Create test client."""
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(test_db):
    """Create test user."""
    from api.auth import create_user
    user = create_user(
        db=test_db,
        email="test@example.com",
        password="testpassword",
        full_name="Test User"
    )
    return user

@pytest.fixture(scope="function")
def test_superuser(test_db):
    """Create test superuser."""
    from api.auth import create_user
    user = create_user(
        db=test_db,
        email="admin@example.com",
        password="adminpassword",
        full_name="Admin User",
        is_superuser=True
    )
    return user

@pytest.fixture(scope="function")
def test_api_key(test_db, test_user):
    """Create test API key."""
    from api.models import APIKey
    api_key = APIKey(
        user_id=test_user.id,
        key="test_api_key",
        name="Test API Key"
    )
    test_db.add(api_key)
    test_db.commit()
    test_db.refresh(api_key)
    return api_key

@pytest.fixture(scope="function")
def auth_headers(test_user):
    """Create authentication headers."""
    from api.auth import create_access_token
    access_token = create_access_token(
        data={"sub": test_user.email}
    )
    return {"Authorization": f"Bearer {access_token}"} 