"""
Tests for POST /api/auth/login

Covers: happy path returns 200 with TokenOut, wrong email → 401,
wrong password → 401, missing fields → 422.
Verifies the returned token is a valid HS256 JWT with correct claims.
"""
import os
from unittest.mock import patch

import pytest
from jose import jwt

TEST_SECRET = os.environ["JWT_SECRET"]
TEST_ALGORITHM = os.environ["JWT_ALGORITHM"]
LOGIN_URL = "/api/auth/login"


class TestLoginHappyPath:
    def test_valid_credentials_return_200(self, client, sample_attorney_dict):
        with patch(
            "app.repositories.attorney_repository.get_by_email",
            return_value=sample_attorney_dict,
        ):
            response = client.post(
                LOGIN_URL,
                json={"email": "attorney@example.com", "password": "correctpassword"},
            )
        assert response.status_code == 200

    def test_response_contains_access_token(self, client, sample_attorney_dict):
        with patch(
            "app.repositories.attorney_repository.get_by_email",
            return_value=sample_attorney_dict,
        ):
            response = client.post(
                LOGIN_URL,
                json={"email": "attorney@example.com", "password": "correctpassword"},
            )
        assert "access_token" in response.json()

    def test_response_token_type_is_bearer(self, client, sample_attorney_dict):
        with patch(
            "app.repositories.attorney_repository.get_by_email",
            return_value=sample_attorney_dict,
        ):
            response = client.post(
                LOGIN_URL,
                json={"email": "attorney@example.com", "password": "correctpassword"},
            )
        assert response.json()["token_type"] == "bearer"

    def test_returned_token_is_decodable(self, client, sample_attorney_dict):
        with patch(
            "app.repositories.attorney_repository.get_by_email",
            return_value=sample_attorney_dict,
        ):
            response = client.post(
                LOGIN_URL,
                json={"email": "attorney@example.com", "password": "correctpassword"},
            )
        token = response.json()["access_token"]
        claims = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert "sub" in claims
        assert "email" in claims
        assert "exp" in claims

    def test_token_sub_equals_attorney_id(self, client, sample_attorney_dict):
        with patch(
            "app.repositories.attorney_repository.get_by_email",
            return_value=sample_attorney_dict,
        ):
            response = client.post(
                LOGIN_URL,
                json={"email": "attorney@example.com", "password": "correctpassword"},
            )
        token = response.json()["access_token"]
        claims = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGORITHM])
        assert claims["sub"] == sample_attorney_dict["id"]


class TestLoginFailureModes:
    def test_unknown_email_returns_401(self, client):
        with patch(
            "app.repositories.attorney_repository.get_by_email",
            return_value=None,
        ):
            response = client.post(
                LOGIN_URL,
                json={"email": "nobody@example.com", "password": "whatever"},
            )
        assert response.status_code == 401

    def test_wrong_password_returns_401(self, client, sample_attorney_dict):
        with patch(
            "app.repositories.attorney_repository.get_by_email",
            return_value=sample_attorney_dict,
        ):
            response = client.post(
                LOGIN_URL,
                json={"email": "attorney@example.com", "password": "wrongpassword"},
            )
        assert response.status_code == 401

    def test_missing_email_returns_422(self, client):
        response = client.post(LOGIN_URL, json={"password": "secret"})
        assert response.status_code == 422

    def test_missing_password_returns_422(self, client):
        response = client.post(LOGIN_URL, json={"email": "attorney@example.com"})
        assert response.status_code == 422

    def test_invalid_email_format_returns_422(self, client):
        response = client.post(
            LOGIN_URL,
            json={"email": "not-an-email", "password": "secret"},
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, client):
        response = client.post(LOGIN_URL, json={})
        assert response.status_code == 422
