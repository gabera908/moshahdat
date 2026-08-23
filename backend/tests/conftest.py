"""Shared test fixtures: isolated SQLite database + API client + auth helpers."""
import os

# Must be set BEFORE app modules import settings.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_platform.db")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-1234")
os.environ.setdefault("CORS_ORIGINS", "http://testclient")

import pytest
from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine, get_db
from app.main import create_app
from app.models import Category, User, UserRole

# Start from a clean schema every test run.
if os.path.exists("./test_platform.db"):
    os.remove("./test_platform.db")


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """Create the full schema on SQLite for the test session."""
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Each test starts with a clean rate-limit window."""
    from app.core.ratelimit import limiter

    limiter._hits.clear()
    yield
    limiter._hits.clear()


@pytest.fixture()
def db():
    """Fresh transactional-ish session per test (cleanup between tests)."""
    connection = engine.connect()
    session = SessionLocal(bind=connection)
    yield session
    session.close()
    # Wipe all data between tests while keeping the schema.
    for table in reversed(Base.metadata.sorted_tables):
        connection.execute(table.delete())
    connection.commit()
    connection.close()


@pytest.fixture()
def client(db):
    """TestClient wired to the test database."""
    app = create_app()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db):
    user = User(
        username="admin_test",
        email="admin@test.local",
        password_hash=hash_password("AdminPass123"),
        full_name="مدير الاختبار",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def editor_user(db):
    user = User(
        username="editor_test",
        email="editor@test.local",
        password_hash=hash_password("EditorPass123"),
        full_name="محرر",
        role=UserRole.EDITOR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


def login(client, username: str, password: str) -> dict:
    resp = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    return body["data"]


def auth_headers(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture()
def admin_headers(client, admin_user):
    return auth_headers(login(client, "admin_test", "AdminPass123"))


@pytest.fixture()
def editor_headers(client, editor_user):
    return auth_headers(login(client, "editor_test", "EditorPass123"))


@pytest.fixture()
def moderator_user(db):
    user = User(
        username="moderator_test",
        email="mod@test.local",
        password_hash=hash_password("ModPass1234"),
        full_name="مشرف",
        role=UserRole.MODERATOR,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return user


@pytest.fixture()
def moderator_setup(client, moderator_user):
    tokens = login(client, "moderator_test", "ModPass1234")
    return auth_headers(tokens)


@pytest.fixture()
def category(db):
    cat = Category(name="وثائقي", slug="doc")
    db.add(cat)
    db.commit()
    return cat
