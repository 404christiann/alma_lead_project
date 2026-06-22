"""
Shared fixtures for the entire test suite.
Env vars are set here before any app module is imported so that
pydantic-settings can read them. Nothing in this file imports from app/.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest

# ---------------------------------------------------------------------------
# Environment — must be set before any app.* import
# ---------------------------------------------------------------------------
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/testdb")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only-32chars!")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "480")
os.environ.setdefault("RESEND_API_KEY", "re_test_000000000000000000000000")
os.environ.setdefault("ATTORNEY_EMAIL", "attorney@example.com")
os.environ.setdefault("RESEND_FROM_EMAIL", "noreply@example.com")
os.environ.setdefault("MINIO_ENDPOINT_URL", "http://minio:9000")
os.environ.setdefault("MINIO_PUBLIC_URL", "http://localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "minioadmin")
os.environ.setdefault("MINIO_SECRET_KEY", "minioadmin")
os.environ.setdefault("MINIO_BUCKET", "resumes")
os.environ.setdefault("PRESIGNED_URL_TTL_SECONDS", "3600")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:3000"]')
os.environ.setdefault("MAX_FILE_BYTES", str(10 * 1024 * 1024))

TEST_JWT_SECRET = os.environ["JWT_SECRET"]
TEST_JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]

SAMPLE_ATTORNEY_ID = str(uuid.uuid4())
SAMPLE_LEAD_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# File byte fixtures — real magic bytes so python-magic sniffs correctly
# ---------------------------------------------------------------------------

@pytest.fixture
def pdf_bytes():
    """Minimal bytes that start with the PDF magic signature."""
    return b"%PDF-1.4 " + b"x" * 200


@pytest.fixture
def png_bytes():
    """Minimal bytes that start with the PNG magic signature."""
    return b"\x89PNG\r\n\x1a\n" + b"\x00" * 200


@pytest.fixture
def jpg_bytes():
    """Minimal bytes that start with the JPEG magic signature."""
    return b"\xff\xd8\xff\xe0" + b"\x00" * 200


@pytest.fixture
def docx_bytes():
    """DOCX is ZIP-based; starts with the PK magic signature."""
    return b"PK\x03\x04" + b"\x00" * 200


@pytest.fixture
def oversize_bytes():
    """One byte over the 10 MB limit."""
    return b"x" * (10 * 1024 * 1024 + 1)


@pytest.fixture
def exe_bytes():
    """Windows PE magic bytes — must be rejected."""
    return b"MZ" + b"\x00" * 200


# ---------------------------------------------------------------------------
# Domain data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_lead_dict():
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": SAMPLE_LEAD_ID,
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "resume_path": f"resumes/{SAMPLE_LEAD_ID}/resume.pdf",
        "resume_filename": "resume.pdf",
        "resume_content_type": "application/pdf",
        "status": "PENDING",
        "status_updated_at": now,
        "created_at": now,
        "updated_at": now,
    }


@pytest.fixture
def sample_lead_dict_no_resume(sample_lead_dict):
    return {
        **sample_lead_dict,
        "resume_path": None,
        "resume_filename": None,
        "resume_content_type": None,
    }


@pytest.fixture
def sample_lead_dict_reached_out(sample_lead_dict):
    return {**sample_lead_dict, "status": "REACHED_OUT"}


@pytest.fixture
def sample_attorney_dict():
    import bcrypt
    pw_hash = bcrypt.hashpw(b"correctpassword", bcrypt.gensalt()).decode()
    return {
        "id": SAMPLE_ATTORNEY_ID,
        "email": "attorney@example.com",
        "password_hash": pw_hash,
    }


# ---------------------------------------------------------------------------
# JWT fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_jwt_token():
    from jose import jwt
    payload = {
        "sub": SAMPLE_ATTORNEY_ID,
        "email": "attorney@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=480),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)


@pytest.fixture
def expired_jwt_token():
    from jose import jwt
    payload = {
        "sub": SAMPLE_ATTORNEY_ID,
        "email": "attorney@example.com",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)


@pytest.fixture
def wrong_secret_jwt_token():
    from jose import jwt
    payload = {
        "sub": SAMPLE_ATTORNEY_ID,
        "email": "attorney@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=480),
    }
    return jwt.encode(payload, "completely-wrong-secret", algorithm=TEST_JWT_ALGORITHM)


@pytest.fixture
def auth_headers(valid_jwt_token):
    return {"Authorization": f"Bearer {valid_jwt_token}"}
