"""
Tests for app/services/auth_service.py

Covers: create_access_token returns a valid, decodable JWT with the correct
claims (sub, email, exp) using HS256.
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
from jose import jwt

from app.services.auth_service import create_access_token

TEST_SECRET = os.environ["JWT_SECRET"]
TEST_ALGORITHM = os.environ["JWT_ALGORITHM"]
ATTORNEY_ID = uuid.uuid4()
ATTORNEY_EMAIL = "attorney@example.com"


class TestCreateAccessToken:
    def test_returns_a_string(self):
        token = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        assert isinstance(token, str)

    def test_token_is_decodable_with_correct_secret(self):
        token = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        claims = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert claims is not None

    def test_sub_claim_equals_str_of_attorney_id(self):
        token = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        claims = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert claims["sub"] == str(ATTORNEY_ID)

    def test_email_claim_present_and_correct(self):
        token = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        claims = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert claims["email"] == ATTORNEY_EMAIL

    def test_exp_claim_is_in_the_future(self):
        token = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        claims = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert claims["exp"] > datetime.now(timezone.utc).timestamp()

    def test_token_uses_hs256_algorithm(self):
        token = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "HS256"

    def test_wrong_secret_raises_on_decode(self):
        from jose import JWTError
        token = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        with pytest.raises(JWTError):
            jwt.decode(token, "completely-wrong-secret", algorithms=[TEST_ALGORITHM])

    def test_different_attorney_ids_produce_different_tokens(self):
        other_id = uuid.uuid4()
        t1 = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        t2 = create_access_token(other_id, "other@example.com")
        assert t1 != t2

    def test_token_has_three_segments(self):
        token = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        assert len(token.split(".")) == 3

    def test_exp_is_approximately_480_minutes_from_now(self):
        import time
        token = create_access_token(ATTORNEY_ID, ATTORNEY_EMAIL)
        claims = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        now = time.time()
        expires_in_minutes = (claims["exp"] - now) / 60
        # Allow ±1 minute drift
        assert 479 <= expires_in_minutes <= 481
