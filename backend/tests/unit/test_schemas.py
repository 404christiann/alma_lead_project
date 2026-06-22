"""
Tests for app/schemas/lead.py and app/schemas/auth.py

Covers: LeadCreate field validators (strip, lowercase, non-empty),
StatusUpdateIn, LeadOut shape, LoginIn, TokenOut.
"""
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.lead import LeadCreate, StatusUpdateIn, LeadOut, LeadListItem, ErrorResponse
from app.schemas.auth import LoginIn, TokenOut
from app.models.lead import LeadStatus


class TestLeadCreateStripping:
    def test_strips_leading_trailing_whitespace_from_first_name(self):
        lead = LeadCreate(first_name="  Jane  ", last_name="Doe", email="jane@example.com")
        assert lead.first_name == "Jane"

    def test_strips_leading_trailing_whitespace_from_last_name(self):
        lead = LeadCreate(first_name="Jane", last_name="  Doe  ", email="jane@example.com")
        assert lead.last_name == "Doe"

    def test_strips_whitespace_from_email(self):
        lead = LeadCreate(first_name="Jane", last_name="Doe", email="  jane@example.com  ")
        assert lead.email == "jane@example.com"


class TestLeadCreateEmailNormalization:
    def test_lowercases_entire_email(self):
        lead = LeadCreate(first_name="Jane", last_name="Doe", email="JANE@EXAMPLE.COM")
        assert lead.email == "jane@example.com"

    def test_lowercases_local_part(self):
        lead = LeadCreate(first_name="Jane", last_name="Doe", email="Jane.Doe@example.com")
        assert lead.email == "jane.doe@example.com"

    def test_lowercases_domain_part(self):
        lead = LeadCreate(first_name="Jane", last_name="Doe", email="jane@EXAMPLE.COM")
        assert lead.email == "jane@example.com"

    def test_mixed_case_fully_lowercased(self):
        lead = LeadCreate(first_name="Jane", last_name="Doe", email="Jane.Doe@Example.COM")
        assert lead.email == "jane.doe@example.com"


class TestLeadCreateValidation:
    def test_rejects_empty_first_name(self):
        with pytest.raises(ValidationError):
            LeadCreate(first_name="", last_name="Doe", email="jane@example.com")

    def test_rejects_whitespace_only_first_name(self):
        with pytest.raises(ValidationError):
            LeadCreate(first_name="   ", last_name="Doe", email="jane@example.com")

    def test_rejects_empty_last_name(self):
        with pytest.raises(ValidationError):
            LeadCreate(first_name="Jane", last_name="", email="jane@example.com")

    def test_rejects_whitespace_only_last_name(self):
        with pytest.raises(ValidationError):
            LeadCreate(first_name="Jane", last_name="   ", email="jane@example.com")

    def test_rejects_invalid_email_format(self):
        with pytest.raises(ValidationError):
            LeadCreate(first_name="Jane", last_name="Doe", email="not-an-email")

    def test_rejects_email_missing_domain(self):
        with pytest.raises(ValidationError):
            LeadCreate(first_name="Jane", last_name="Doe", email="jane@")

    def test_rejects_missing_first_name(self):
        with pytest.raises(ValidationError):
            LeadCreate(last_name="Doe", email="jane@example.com")

    def test_rejects_missing_last_name(self):
        with pytest.raises(ValidationError):
            LeadCreate(first_name="Jane", email="jane@example.com")

    def test_rejects_missing_email(self):
        with pytest.raises(ValidationError):
            LeadCreate(first_name="Jane", last_name="Doe")

    def test_valid_lead_creates_successfully(self):
        lead = LeadCreate(first_name="Jane", last_name="Doe", email="jane@example.com")
        assert lead.first_name == "Jane"
        assert lead.last_name == "Doe"
        assert lead.email == "jane@example.com"


class TestStatusUpdateIn:
    def test_accepts_reached_out(self):
        s = StatusUpdateIn(status=LeadStatus.REACHED_OUT)
        assert s.status == LeadStatus.REACHED_OUT

    def test_accepts_pending(self):
        # Schema accepts any LeadStatus; transition logic enforced in route
        s = StatusUpdateIn(status=LeadStatus.PENDING)
        assert s.status == LeadStatus.PENDING

    def test_rejects_invalid_status_string(self):
        with pytest.raises(ValidationError):
            StatusUpdateIn(status="INVALID_STATUS")

    def test_rejects_missing_status(self):
        with pytest.raises(ValidationError):
            StatusUpdateIn()


class TestLeadOut:
    def test_has_all_required_fields(self):
        now = datetime.now(timezone.utc)
        lead = LeadOut(
            id=uuid.uuid4(),
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            status=LeadStatus.PENDING,
            status_updated_at=now,
            created_at=now,
            resume_filename=None,
            resume_url=None,
        )
        assert lead.status == LeadStatus.PENDING

    def test_resume_url_is_optional(self):
        now = datetime.now(timezone.utc)
        lead = LeadOut(
            id=uuid.uuid4(),
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            status=LeadStatus.PENDING,
            status_updated_at=now,
            created_at=now,
            resume_filename=None,
            resume_url=None,
        )
        assert lead.resume_url is None

    def test_resume_filename_is_optional(self):
        now = datetime.now(timezone.utc)
        lead = LeadOut(
            id=uuid.uuid4(),
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            status=LeadStatus.PENDING,
            status_updated_at=now,
            created_at=now,
            resume_filename=None,
            resume_url=None,
        )
        assert lead.resume_filename is None

    def test_does_not_expose_updated_at(self):
        # updated_at is internal; LeadOut must not include it
        fields = LeadOut.model_fields.keys()
        assert "updated_at" not in fields

    def test_does_not_expose_resume_content_type_directly(self):
        fields = LeadOut.model_fields.keys()
        assert "resume_content_type" not in fields


class TestLeadListItem:
    def test_has_no_resume_url(self):
        # List items do not include resume_url (only detail view does)
        fields = LeadListItem.model_fields.keys()
        assert "resume_url" not in fields

    def test_has_required_list_fields(self):
        fields = set(LeadListItem.model_fields.keys())
        required = {"id", "first_name", "last_name", "email", "status", "created_at", "status_updated_at"}
        assert required.issubset(fields)


class TestErrorResponse:
    def test_has_detail_field(self):
        err = ErrorResponse(detail="something went wrong")
        assert err.detail == "something went wrong"


class TestLoginIn:
    def test_accepts_valid_credentials(self):
        login = LoginIn(email="attorney@example.com", password="secret")
        assert login.email == "attorney@example.com"
        assert login.password == "secret"

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            LoginIn(email="not-an-email", password="secret")

    def test_rejects_missing_password(self):
        with pytest.raises(ValidationError):
            LoginIn(email="attorney@example.com")

    def test_rejects_missing_email(self):
        with pytest.raises(ValidationError):
            LoginIn(password="secret")


class TestTokenOut:
    def test_default_token_type_is_bearer(self):
        token = TokenOut(access_token="abc.def.ghi")
        assert token.token_type == "bearer"

    def test_access_token_stored(self):
        token = TokenOut(access_token="abc.def.ghi")
        assert token.access_token == "abc.def.ghi"
