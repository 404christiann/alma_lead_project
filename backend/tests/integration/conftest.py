"""
Fixtures for integration (route) tests.

Provides:
  - mock_conn: MagicMock psycopg2 connection
  - client: unauthenticated TestClient with get_db_conn overridden
  - auth_client: client that also overrides get_current_attorney
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

MOCK_ATTORNEY_CLAIMS = {
    "sub": "00000000-0000-0000-0000-000000000001",
    "email": "attorney@example.com",
}


@pytest.fixture
def mock_conn():
    """Mock psycopg2 connection returned by get_db_conn."""
    return MagicMock()


@pytest.fixture
def client(mock_conn):
    """
    TestClient with the DB dependency overridden.
    Startup lifespan (pool + MinIO bucket) is patched out so no real
    services are required.
    """
    with (
        patch("app.db.psycopg2"),
        patch("app.services.storage_service.ensure_bucket"),
    ):
        from app.main import app
        from app.db import get_db_conn

        def override_get_db_conn():
            yield mock_conn

        app.dependency_overrides[get_db_conn] = override_get_db_conn
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
        app.dependency_overrides.clear()


@pytest.fixture
def auth_client(mock_conn):
    """
    TestClient where get_db_conn AND get_current_attorney are overridden.
    Use this for all protected-route tests.
    """
    with (
        patch("app.db.psycopg2"),
        patch("app.services.storage_service.ensure_bucket"),
    ):
        from app.main import app
        from app.db import get_db_conn
        from app.api.deps import get_current_attorney

        def override_get_db_conn():
            yield mock_conn

        async def override_get_current_attorney():
            return MOCK_ATTORNEY_CLAIMS

        app.dependency_overrides[get_db_conn] = override_get_db_conn
        app.dependency_overrides[get_current_attorney] = override_get_current_attorney
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c
        app.dependency_overrides.clear()
