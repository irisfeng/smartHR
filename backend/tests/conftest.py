import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Override env before importing app modules
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["MINERU_API_KEY"] = ""
os.environ["AI_API_KEY"] = ""

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.auth import hash_password, create_access_token

# In-memory SQLite with StaticPool so all sessions share the same database
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a test database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """Provide a test HTTP client."""
    return TestClient(app)


@pytest.fixture
def manager_user(db) -> User:
    """Create and return a manager user."""
    user = User(
        username="test_manager",
        password_hash=hash_password("password123"),
        role="manager",
        display_name="Test Manager",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def hr_user(db) -> User:
    """Create and return an HR user."""
    user = User(
        username="test_hr",
        password_hash=hash_password("password123"),
        role="hr",
        display_name="Test HR",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def manager_token(manager_user) -> str:
    """Return a valid access token for the manager user."""
    return create_access_token(manager_user.id, manager_user.role)


@pytest.fixture
def hr_token(hr_user) -> str:
    """Return a valid access token for the HR user."""
    return create_access_token(hr_user.id, hr_user.role)


@pytest.fixture
def manager_headers(manager_token) -> dict:
    """Return auth headers for manager."""
    return {"Authorization": f"Bearer {manager_token}"}


@pytest.fixture
def hr_headers(hr_token) -> dict:
    """Return auth headers for HR user."""
    return {"Authorization": f"Bearer {hr_token}"}
