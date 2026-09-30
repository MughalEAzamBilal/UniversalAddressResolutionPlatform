import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
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
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


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


class TestResponseWrapper:
    def __init__(self, response):
        self._r = response
        cookie_dict = {}
        for cookie_str in response.headers.getlist("Set-Cookie"):
            parts = cookie_str.split(";")[0].split("=", 1)
            if len(parts) == 2:
                cookie_dict[parts[0].strip()] = parts[1].strip()
        self.cookies = cookie_dict

    def __getattr__(self, name):
        return getattr(self._r, name)

    def json(self):
        return self._r.get_json(silent=True)

    @property
    def text(self):
        return self._r.get_data(as_text=True)


class FlaskTestClientWrapper:
    def __init__(self, flask_client):
        self._c = flask_client

    def _prepare_kwargs(self, kwargs):
        cookies = kwargs.pop("cookies", None)
        if cookies:
            for k, v in cookies.items():
                self._c.set_cookie(k, v)
        return kwargs

    def get(self, *args, **kwargs):
        kwargs = self._prepare_kwargs(kwargs)
        res = self._c.get(*args, **kwargs)
        return TestResponseWrapper(res)

    def post(self, *args, **kwargs):
        kwargs = self._prepare_kwargs(kwargs)
        res = self._c.post(*args, **kwargs)
        return TestResponseWrapper(res)

    def put(self, *args, **kwargs):
        kwargs = self._prepare_kwargs(kwargs)
        res = self._c.put(*args, **kwargs)
        return TestResponseWrapper(res)

    def delete(self, *args, **kwargs):
        kwargs = self._prepare_kwargs(kwargs)
        res = self._c.delete(*args, **kwargs)
        return TestResponseWrapper(res)


@pytest.fixture(scope="function")
def client(db_session, monkeypatch):
    """Flask test client with overridden database session."""
    import app.database.session as session_mod
    monkeypatch.setattr(session_mod, "get_db", lambda: db_session)
    monkeypatch.setattr(session_mod, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(session_mod, "close_db", lambda e=None: None)

    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield FlaskTestClientWrapper(test_client)


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
