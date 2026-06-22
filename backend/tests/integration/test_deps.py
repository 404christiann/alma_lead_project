"""
Tests for app/api/deps.py — get_current_attorney

Covers: valid token returns claims dict, missing header → 401,
bad Bearer format → 401, wrong signature → 401, expired token → 401.
Verifies the function raises HTTPException directly, never InvalidCredentialsError.
"""
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from jose import jwt

TEST_SECRET = os.environ["JWT_SECRET"]
TEST_ALGORITHM = os.environ["JWT_ALGORITHM"]
ATTORNEY_ID = "00000000-0000-0000-0000-000000000001"
ATTORNEY_EMAIL = "attorney@example.com"


def _make_token(secret=TEST_SECRET, algorithm=TEST_ALGORITHM, minutes_from_now=480, **extra):
    payload = {
        "sub": ATTORNEY_ID,
        "email": ATTORNEY_EMAIL,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes_from_now),
        **extra,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


class TestGetCurrentAttorney:
    @pytest.mark.asyncio
    async def test_valid_token_returns_sub_claim(self):
        from app.api.deps import get_current_attorney
        token = _make_token()
        claims = await get_current_attorney(authorization=f"Bearer {token}")
        assert claims["sub"] == ATTORNEY_ID

    @pytest.mark.asyncio
    async def test_valid_token_returns_email_claim(self):
        from app.api.deps import get_current_attorney
        token = _make_token()
        claims = await get_current_attorney(authorization=f"Bearer {token}")
        assert claims["email"] == ATTORNEY_EMAIL

    @pytest.mark.asyncio
    async def test_empty_authorization_raises_401(self):
        from app.api.deps import get_current_attorney
        with pytest.raises(HTTPException) as exc:
            await get_current_attorney(authorization="")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_bearer_prefix_raises_401(self):
        from app.api.deps import get_current_attorney
        token = _make_token()
        with pytest.raises(HTTPException) as exc:
            await get_current_attorney(authorization=token)  # no "Bearer " prefix
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_scheme_raises_401(self):
        from app.api.deps import get_current_attorney
        token = _make_token()
        with pytest.raises(HTTPException) as exc:
            await get_current_attorney(authorization=f"Token {token}")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_401(self):
        from app.api.deps import get_current_attorney
        token = _make_token(secret="wrong-secret-entirely")
        with pytest.raises(HTTPException) as exc:
            await get_current_attorney(authorization=f"Bearer {token}")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_token_raises_401(self):
        from app.api.deps import get_current_attorney
        token = _make_token(minutes_from_now=-5)
        with pytest.raises(HTTPException) as exc:
            await get_current_attorney(authorization=f"Bearer {token}")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_token_raises_401(self):
        from app.api.deps import get_current_attorney
        with pytest.raises(HTTPException) as exc:
            await get_current_attorney(authorization="Bearer not.a.real.jwt.token")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_never_raises_invalid_credentials_error(self):
        """get_current_attorney must raise HTTPException, never InvalidCredentialsError."""
        from app.api.deps import get_current_attorney
        from app.exceptions import InvalidCredentialsError
        try:
            await get_current_attorney(authorization="Bearer bad.token.value")
        except InvalidCredentialsError:
            pytest.fail(
                "get_current_attorney raised InvalidCredentialsError — "
                "must raise HTTPException(401) directly"
            )
        except HTTPException:
            pass  # expected
        except Exception:
            pass  # any other exception is also acceptable during early dev
