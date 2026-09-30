import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.user import User, UserRole, AccountStatus
from app.services.edit_id_service import EditIdService
from app.core.security import hash_password, hash_edit_id

# In-memory SQLite engine for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database tables for each test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden database session dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session):
    """Standard test user matching prompt scenario."""
    dob = date(1991, 1, 1)
    edit_id = EditIdService.generate_edit_id("ab1226", "Muhammad", "Ayesha", "123", dob)
    assert edit_id == "ab1226MA12391"
    user = User(
        username="bilal",
        email="bilal@example.com",
        public_id="ab1226",
        full_name="Muhammad Bilal",
        father_name="Muhammad",
        mother_name="Ayesha",
        cnic_or_id_card="123",
        date_of_birth=dob,
        password_hash=hash_password("UserPass123!"),
        edit_id_hash=hash_edit_id(edit_id),
        role=UserRole.USER,
        account_status=AccountStatus.ACTIVE
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
