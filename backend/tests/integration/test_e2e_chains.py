"""
End-to-end chain tests: verify that components work correctly when multiple
requests are chained and the output of one step feeds the next.

These tests catch gaps that isolated route tests (which mock every dependency
independently) cannot surface — e.g. the JWT sign/verify round-trip, correct
UUID threading through compensation, and email normalization reaching insert_lead.
"""
import os
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from jose import jwt

LEADS_URL = "/api/leads"
PRESIGNED_URL = "http://localhost:9000/resumes/test/resume.pdf?sig=abc"

_JWT_SECRET = os.environ["JWT_SECRET"]
_JWT_ALGORITHM = os.environ["JWT_ALGORITHM"]


def _make_token(**extra):
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "attorney@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        **extra,
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def _post_lead(client, pdf_bytes, lead_dict, email="jane@example.com", path="resumes/lead/resume.pdf"):
    """POST /api/leads with all I/O mocked. Returns the response."""
    with (
        patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
        patch("app.repositories.lead_repository.insert_lead", return_value=lead_dict),
        patch("app.services.storage_service.upload_resume", return_value=path),
        patch("app.repositories.lead_repository.update_resume_info", return_value=lead_dict),
        patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
        patch("app.services.email_service.send_prospect_confirmation", return_value=True),
        patch("app.services.email_service.send_attorney_notification", return_value=True),
    ):
        return client.post(
            LEADS_URL,
            data={"first_name": "Jane", "last_name": "Doe", "email": email},
            files={"resume": ("resume.pdf", pdf_bytes, "application/pdf")},
        )


# ---------------------------------------------------------------------------
# Chain 1 — Login → real JWT → protected route (no mock on get_current_attorney)
# ---------------------------------------------------------------------------

class TestLoginToProtectedRouteChain:
    def test_token_from_login_authorizes_list_leads(self, client, sample_attorney_dict, sample_lead_dict):
        """
        Login with real bcrypt + real JWT signing, then use the returned token
        on GET /api/leads WITHOUT mocking get_current_attorney.
        Tests the full sign/verify round-trip that isolated tests never exercise.
        """
        with patch("app.repositories.attorney_repository.get_by_email", return_value=sample_attorney_dict):
            login_res = client.post(
                "/api/auth/login",
                json={"email": "attorney@example.com", "password": "correctpassword"},
            )
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]

        # get_current_attorney is NOT mocked — real JWT decode runs
        with patch("app.repositories.lead_repository.list_leads", return_value=[sample_lead_dict]):
            leads_res = client.get(LEADS_URL, headers={"Authorization": f"Bearer {token}"})
        assert leads_res.status_code == 200

    def test_token_from_login_carries_correct_email_claim(self, client, sample_attorney_dict):
        """Token returned by login must encode the attorney email, not an empty or wrong value."""
        with patch("app.repositories.attorney_repository.get_by_email", return_value=sample_attorney_dict):
            res = client.post(
                "/api/auth/login",
                json={"email": "attorney@example.com", "password": "correctpassword"},
            )
        token = res.json()["access_token"]
        claims = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        assert claims["email"] == sample_attorney_dict["email"]

    def test_tampered_token_is_rejected(self, client, sample_lead_dict):
        """A valid-looking token signed with a different secret must get 401, not 200."""
        bad_token = jwt.encode(
            {"sub": str(uuid.uuid4()), "email": "a@a.com", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            "completely-wrong-secret",
            algorithm=_JWT_ALGORITHM,
        )
        with patch("app.repositories.lead_repository.list_leads", return_value=[sample_lead_dict]):
            res = client.get(LEADS_URL, headers={"Authorization": f"Bearer {bad_token}"})
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# Chain 2 — Create lead → detail fetch uses the same UUID
# ---------------------------------------------------------------------------

class TestCreateToDetailChain:
    def test_create_lead_id_is_reachable_via_detail_route(self, client, pdf_bytes, sample_lead_dict):
        """
        The UUID in the POST /api/leads response must be accepted by
        GET /api/leads/{id} and appear in that response too.
        Tests that the route correctly threads the id through.
        """
        create_res = _post_lead(client, pdf_bytes, sample_lead_dict)
        assert create_res.status_code == 201
        lead_id = create_res.json()["id"]

        token = _make_token()
        with (
            patch("app.repositories.lead_repository.get_lead_by_id", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
        ):
            detail_res = client.get(f"{LEADS_URL}/{lead_id}", headers={"Authorization": f"Bearer {token}"})
        assert detail_res.status_code == 200
        assert detail_res.json()["id"] == lead_id

    def test_newly_created_lead_has_pending_status(self, client, pdf_bytes, sample_lead_dict):
        """Regardless of other fields, a freshly created lead must always be PENDING."""
        create_res = _post_lead(client, pdf_bytes, sample_lead_dict)
        assert create_res.json()["status"] == "PENDING"


# ---------------------------------------------------------------------------
# Chain 3 — Status transition lifecycle
# ---------------------------------------------------------------------------

class TestStatusTransitionChain:
    def test_pending_lead_transitions_to_reached_out(
        self, auth_client, sample_lead_dict, sample_lead_dict_reached_out
    ):
        """
        PATCH on a PENDING lead: route reads current status → can_transition →
        update_status → response serializes REACHED_OUT correctly.
        """
        lead_id = sample_lead_dict["id"]
        with (
            patch("app.repositories.lead_repository.get_lead_by_id", return_value=sample_lead_dict),
            patch("app.repositories.lead_repository.update_status", return_value=sample_lead_dict_reached_out),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
        ):
            res = auth_client.patch(f"{LEADS_URL}/{lead_id}/status", json={"status": "REACHED_OUT"})
        assert res.status_code == 200
        assert res.json()["status"] == "REACHED_OUT"

    def test_remark_reached_out_returns_409(self, auth_client, sample_lead_dict_reached_out):
        """
        Second PATCH on an already-REACHED_OUT lead must return 409.
        The guard must fire before any DB write.
        """
        lead_id = sample_lead_dict_reached_out["id"]
        with patch(
            "app.repositories.lead_repository.get_lead_by_id",
            return_value=sample_lead_dict_reached_out,
        ):
            res = auth_client.patch(f"{LEADS_URL}/{lead_id}/status", json={"status": "REACHED_OUT"})
        assert res.status_code == 409

    def test_remark_reached_out_skips_update_status_call(self, auth_client, sample_lead_dict_reached_out):
        """
        When the transition is illegal, update_status must NOT be called —
        verifies the guard check happens before the DB write, not after.
        """
        lead_id = sample_lead_dict_reached_out["id"]
        with (
            patch(
                "app.repositories.lead_repository.get_lead_by_id",
                return_value=sample_lead_dict_reached_out,
            ),
            patch("app.repositories.lead_repository.update_status") as mock_update,
        ):
            auth_client.patch(f"{LEADS_URL}/{lead_id}/status", json={"status": "REACHED_OUT"})
        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# Chain 4 — Compensation: correct IDs are threaded through delete calls
# ---------------------------------------------------------------------------

class TestCompensationChain:
    def test_upload_failure_deletes_the_exact_inserted_lead_id(self, client, pdf_bytes, sample_lead_dict):
        """
        When upload_resume raises StorageError, delete_lead must receive the UUID
        that insert_lead returned — not a different or hardcoded value.
        Catches any regression where compensation uses the wrong variable.
        """
        from app.exceptions import StorageError

        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", side_effect=StorageError("MinIO down")),
            patch("app.repositories.lead_repository.delete_lead") as mock_delete,
        ):
            client.post(
                LEADS_URL,
                data={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
                files={"resume": ("resume.pdf", pdf_bytes, "application/pdf")},
            )

        mock_delete.assert_called_once()
        _, called_id = mock_delete.call_args.args
        assert str(called_id) == sample_lead_dict["id"]

    def test_update_resume_info_failure_passes_correct_path_to_delete_object(
        self, client, pdf_bytes, sample_lead_dict
    ):
        """
        When update_resume_info fails, delete_object must be called with the
        path that upload_resume returned — verifies the path variable is threaded
        correctly through the compensation branch.
        """
        uploaded_path = f"resumes/{sample_lead_dict['id']}/resume.pdf"

        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value=uploaded_path),
            patch("app.repositories.lead_repository.update_resume_info", side_effect=Exception("DB failure")),
            patch("app.services.storage_service.delete_object") as mock_delete_obj,
            patch("app.repositories.lead_repository.delete_lead"),
        ):
            client.post(
                LEADS_URL,
                data={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
                files={"resume": ("resume.pdf", pdf_bytes, "application/pdf")},
            )

        mock_delete_obj.assert_called_once()
        _, _, path_arg = mock_delete_obj.call_args.args
        assert path_arg == uploaded_path

    def test_update_resume_info_failure_also_deletes_lead(self, client, pdf_bytes, sample_lead_dict):
        """Both delete_object AND delete_lead must be called on update_resume_info failure."""
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value="path/resume.pdf"),
            patch("app.repositories.lead_repository.update_resume_info", side_effect=Exception("DB failure")),
            patch("app.services.storage_service.delete_object") as mock_delete_obj,
            patch("app.repositories.lead_repository.delete_lead") as mock_delete_lead,
        ):
            client.post(
                LEADS_URL,
                data={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
                files={"resume": ("resume.pdf", pdf_bytes, "application/pdf")},
            )

        mock_delete_obj.assert_called_once()
        mock_delete_lead.assert_called_once()


# ---------------------------------------------------------------------------
# Chain 5 — Email normalization reaches insert_lead
# ---------------------------------------------------------------------------

class TestEmailNormalizationChain:
    def test_uppercase_email_lowercased_before_insert(self, client, pdf_bytes, sample_lead_dict):
        """
        POST /api/leads with a mixed-case email must call insert_lead with the
        lowercased form. Without this, A@X.COM and a@x.com bypass the unique
        constraint and create duplicate leads for the same person.
        """
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict) as mock_insert,
            patch("app.services.storage_service.upload_resume", return_value="path"),
            patch("app.repositories.lead_repository.update_resume_info", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
            patch("app.services.email_service.send_prospect_confirmation", return_value=True),
            patch("app.services.email_service.send_attorney_notification", return_value=True),
        ):
            client.post(
                LEADS_URL,
                data={"first_name": "Jane", "last_name": "Doe", "email": "JANE@EXAMPLE.COM"},
                files={"resume": ("resume.pdf", pdf_bytes, "application/pdf")},
            )

        _, lead_create_arg = mock_insert.call_args.args
        assert lead_create_arg.email == "jane@example.com"

    def test_mixed_case_email_submission_succeeds(self, client, pdf_bytes, sample_lead_dict):
        """Mixed-case email must not be rejected at the route level — normalization happens first."""
        res = _post_lead(client, pdf_bytes, sample_lead_dict, email="Jane.Doe@EXAMPLE.COM")
        assert res.status_code == 201


# ---------------------------------------------------------------------------
# Route input edge cases (path/query param coercion)
# ---------------------------------------------------------------------------

class TestRouteInputEdgeCases:
    def test_patch_non_uuid_path_returns_422(self, auth_client):
        """PATCH /api/leads/<non-uuid>/status — FastAPI UUID coercion must reject before route runs."""
        res = auth_client.patch("/api/leads/not-a-uuid/status", json={"status": "REACHED_OUT"})
        assert res.status_code == 422

    def test_patch_numeric_id_returns_422(self, auth_client):
        res = auth_client.patch("/api/leads/12345/status", json={"status": "REACHED_OUT"})
        assert res.status_code == 422

    def test_get_lowercase_status_returns_422(self, auth_client):
        """LeadStatus enum only has uppercase values; lowercase must be rejected."""
        res = auth_client.get(f"{LEADS_URL}?status=pending")
        assert res.status_code == 422

    def test_get_mixed_case_status_returns_422(self, auth_client):
        res = auth_client.get(f"{LEADS_URL}?status=Pending")
        assert res.status_code == 422

    def test_get_uppercase_pending_is_accepted(self, auth_client):
        with patch("app.repositories.lead_repository.list_leads", return_value=[]):
            res = auth_client.get(f"{LEADS_URL}?status=PENDING")
        assert res.status_code == 200

    def test_get_uppercase_reached_out_is_accepted(self, auth_client):
        with patch("app.repositories.lead_repository.list_leads", return_value=[]):
            res = auth_client.get(f"{LEADS_URL}?status=REACHED_OUT")
        assert res.status_code == 200
