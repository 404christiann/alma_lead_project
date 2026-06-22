"""
Tests for all lead routes:
  POST   /api/leads              (public)
  GET    /api/leads              (protected)
  GET    /api/leads/{id}         (protected)
  PATCH  /api/leads/{id}/status  (protected)

Uses mock_conn (DB) and patches repository/service functions at source so
the route orchestration logic is exercised without real I/O.
"""
import uuid
from unittest.mock import patch, MagicMock, call

import pytest

LEADS_URL = "/api/leads"
PRESIGNED_URL = "http://localhost:9000/resumes/lead-id/resume.pdf?X-Amz-Signature=abc"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload_form(pdf_bytes, email="jane@example.com", first_name="Jane", last_name="Doe"):
    return (
        {"first_name": first_name, "last_name": last_name, "email": email},
        {"resume": ("resume.pdf", pdf_bytes, "application/pdf")},
    )


def _all_service_patches(lead_dict, path="resumes/lead-id/resume.pdf"):
    """Return a dict of patch targets → return values for a successful POST."""
    return {
        "app.services.file_validator.validate_resume": (".pdf", "application/pdf"),
        "app.repositories.lead_repository.insert_lead": lead_dict,
        "app.services.storage_service.upload_resume": path,
        "app.repositories.lead_repository.update_resume_info": lead_dict,
        "app.services.storage_service.create_presigned_url": PRESIGNED_URL,
        "app.services.email_service.send_prospect_confirmation": True,
        "app.services.email_service.send_attorney_notification": True,
    }


# ---------------------------------------------------------------------------
# POST /api/leads — happy path
# ---------------------------------------------------------------------------

class TestCreateLeadHappyPath:
    def test_returns_201(self, client, pdf_bytes, sample_lead_dict):
        patches = _all_service_patches(sample_lead_dict)
        with (
            patch("app.services.file_validator.validate_resume", return_value=patches["app.services.file_validator.validate_resume"]),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value=patches["app.services.storage_service.upload_resume"]),
            patch("app.repositories.lead_repository.update_resume_info", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
            patch("app.services.email_service.send_prospect_confirmation", return_value=True),
            patch("app.services.email_service.send_attorney_notification", return_value=True),
        ):
            data, files = _upload_form(pdf_bytes)
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 201

    def test_response_contains_id(self, client, pdf_bytes, sample_lead_dict):
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value="path"),
            patch("app.repositories.lead_repository.update_resume_info", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
            patch("app.services.email_service.send_prospect_confirmation", return_value=True),
            patch("app.services.email_service.send_attorney_notification", return_value=True),
        ):
            data, files = _upload_form(pdf_bytes)
            response = client.post(LEADS_URL, data=data, files=files)
        assert "id" in response.json()

    def test_response_status_is_pending(self, client, pdf_bytes, sample_lead_dict):
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value="path"),
            patch("app.repositories.lead_repository.update_resume_info", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
            patch("app.services.email_service.send_prospect_confirmation", return_value=True),
            patch("app.services.email_service.send_attorney_notification", return_value=True),
        ):
            data, files = _upload_form(pdf_bytes)
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.json()["status"] == "PENDING"

    def test_response_contains_resume_url(self, client, pdf_bytes, sample_lead_dict):
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value="path"),
            patch("app.repositories.lead_repository.update_resume_info", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
            patch("app.services.email_service.send_prospect_confirmation", return_value=True),
            patch("app.services.email_service.send_attorney_notification", return_value=True),
        ):
            data, files = _upload_form(pdf_bytes)
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.json()["resume_url"] == PRESIGNED_URL

    def test_uses_sniffed_mime_not_client_content_type(self, client, pdf_bytes, sample_lead_dict):
        """upload_resume must be called with sniffed_mime, not the client-supplied content-type."""
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")) as mock_validate,
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value="path") as mock_upload,
            patch("app.repositories.lead_repository.update_resume_info", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
            patch("app.services.email_service.send_prospect_confirmation", return_value=True),
            patch("app.services.email_service.send_attorney_notification", return_value=True),
        ):
            # Client sends "text/plain" but sniffed MIME is "application/pdf"
            data = {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"}
            files = {"resume": ("resume.pdf", pdf_bytes, "text/plain")}
            client.post(LEADS_URL, data=data, files=files)

        # upload_resume's content_type arg must be "application/pdf" (sniffed), not "text/plain"
        upload_call_kwargs = mock_upload.call_args
        assert upload_call_kwargs is not None
        args = upload_call_kwargs.args if upload_call_kwargs.args else ()
        kwargs = upload_call_kwargs.kwargs if upload_call_kwargs.kwargs else {}
        content_type_arg = kwargs.get("content_type") or (args[5] if len(args) > 5 else None)
        assert content_type_arg == "application/pdf"

    def test_email_failure_still_returns_201(self, client, pdf_bytes, sample_lead_dict):
        """Email errors must not block the 201 response."""
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value="path"),
            patch("app.repositories.lead_repository.update_resume_info", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
            patch("app.services.email_service.send_prospect_confirmation", return_value=False),
            patch("app.services.email_service.send_attorney_notification", return_value=False),
        ):
            data, files = _upload_form(pdf_bytes)
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# POST /api/leads — validation failures (422)
# ---------------------------------------------------------------------------

class TestCreateLeadValidationFailures:
    def test_bad_file_extension_returns_422(self, client, exe_bytes):
        from app.exceptions import FileValidationError
        with patch(
            "app.services.file_validator.validate_resume",
            side_effect=FileValidationError("bad extension"),
        ):
            data = {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"}
            files = {"resume": ("malware.exe", exe_bytes, "application/octet-stream")}
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 422

    def test_oversize_file_returns_422(self, client, oversize_bytes):
        from app.exceptions import FileValidationError
        with patch(
            "app.services.file_validator.validate_resume",
            side_effect=FileValidationError("file too large"),
        ):
            data = {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"}
            files = {"resume": ("big.pdf", oversize_bytes, "application/pdf")}
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 422

    def test_mime_mismatch_returns_422(self, client, jpg_bytes):
        from app.exceptions import FileValidationError
        with patch(
            "app.services.file_validator.validate_resume",
            side_effect=FileValidationError("MIME mismatch"),
        ):
            data = {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"}
            files = {"resume": ("resume.pdf", jpg_bytes, "application/pdf")}
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 422

    def test_empty_first_name_returns_422(self, client, pdf_bytes):
        with patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")):
            data = {"first_name": "", "last_name": "Doe", "email": "jane@example.com"}
            files = {"resume": ("resume.pdf", pdf_bytes, "application/pdf")}
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 422

    def test_whitespace_only_first_name_returns_422(self, client, pdf_bytes):
        with patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")):
            data = {"first_name": "   ", "last_name": "Doe", "email": "jane@example.com"}
            files = {"resume": ("resume.pdf", pdf_bytes, "application/pdf")}
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 422

    def test_invalid_email_returns_422(self, client, pdf_bytes):
        with patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")):
            data = {"first_name": "Jane", "last_name": "Doe", "email": "not-an-email"}
            files = {"resume": ("resume.pdf", pdf_bytes, "application/pdf")}
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 422

    def test_missing_resume_returns_422(self, client):
        response = client.post(
            LEADS_URL,
            data={"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/leads — 409 duplicate email
# ---------------------------------------------------------------------------

class TestCreateLeadDuplicateEmail:
    def test_duplicate_email_returns_409(self, client, pdf_bytes):
        from app.exceptions import DuplicateLeadError
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch(
                "app.repositories.lead_repository.insert_lead",
                side_effect=DuplicateLeadError("email already exists"),
            ),
        ):
            data, files = _upload_form(pdf_bytes)
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 409

    def test_duplicate_email_response_has_detail(self, client, pdf_bytes):
        from app.exceptions import DuplicateLeadError
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch(
                "app.repositories.lead_repository.insert_lead",
                side_effect=DuplicateLeadError("email already exists"),
            ),
        ):
            data, files = _upload_form(pdf_bytes)
            response = client.post(LEADS_URL, data=data, files=files)
        assert "detail" in response.json()


# ---------------------------------------------------------------------------
# POST /api/leads — 500 with compensation
# ---------------------------------------------------------------------------

class TestCreateLeadCompensation:
    def test_upload_failure_returns_500(self, client, pdf_bytes, sample_lead_dict):
        from app.exceptions import StorageError
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch(
                "app.services.storage_service.upload_resume",
                side_effect=StorageError("MinIO down"),
            ),
            patch("app.repositories.lead_repository.delete_lead") as mock_delete,
        ):
            data, files = _upload_form(pdf_bytes)
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 500

    def test_upload_failure_calls_delete_lead(self, client, pdf_bytes, sample_lead_dict):
        from app.exceptions import StorageError
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch(
                "app.services.storage_service.upload_resume",
                side_effect=StorageError("MinIO down"),
            ),
            patch("app.repositories.lead_repository.delete_lead") as mock_delete,
        ):
            data, files = _upload_form(pdf_bytes)
            client.post(LEADS_URL, data=data, files=files)
        mock_delete.assert_called_once()

    def test_update_resume_info_failure_returns_500(self, client, pdf_bytes, sample_lead_dict):
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value="path"),
            patch(
                "app.repositories.lead_repository.update_resume_info",
                side_effect=Exception("DB write failed"),
            ),
            patch("app.services.storage_service.delete_object") as mock_delete_obj,
            patch("app.repositories.lead_repository.delete_lead") as mock_delete_lead,
        ):
            data, files = _upload_form(pdf_bytes)
            response = client.post(LEADS_URL, data=data, files=files)
        assert response.status_code == 500

    def test_update_resume_info_failure_calls_delete_object_and_delete_lead(
        self, client, pdf_bytes, sample_lead_dict
    ):
        with (
            patch("app.services.file_validator.validate_resume", return_value=(".pdf", "application/pdf")),
            patch("app.repositories.lead_repository.insert_lead", return_value=sample_lead_dict),
            patch("app.services.storage_service.upload_resume", return_value="path"),
            patch(
                "app.repositories.lead_repository.update_resume_info",
                side_effect=Exception("DB write failed"),
            ),
            patch("app.services.storage_service.delete_object") as mock_delete_obj,
            patch("app.repositories.lead_repository.delete_lead") as mock_delete_lead,
        ):
            data, files = _upload_form(pdf_bytes)
            client.post(LEADS_URL, data=data, files=files)
        mock_delete_obj.assert_called_once()
        mock_delete_lead.assert_called_once()


# ---------------------------------------------------------------------------
# GET /api/leads — list
# ---------------------------------------------------------------------------

class TestListLeads:
    def test_no_auth_returns_401(self, client):
        response = client.get(LEADS_URL)
        assert response.status_code == 401

    def test_authenticated_returns_200(self, auth_client, sample_lead_dict):
        with patch(
            "app.repositories.lead_repository.list_leads",
            return_value=[sample_lead_dict],
        ):
            response = auth_client.get(LEADS_URL)
        assert response.status_code == 200

    def test_returns_list(self, auth_client, sample_lead_dict):
        with patch(
            "app.repositories.lead_repository.list_leads",
            return_value=[sample_lead_dict],
        ):
            response = auth_client.get(LEADS_URL)
        assert isinstance(response.json(), list)

    def test_filter_by_pending_status(self, auth_client, sample_lead_dict):
        with patch(
            "app.repositories.lead_repository.list_leads",
            return_value=[sample_lead_dict],
        ) as mock_list:
            auth_client.get(f"{LEADS_URL}?status=PENDING")
        mock_list.assert_called_once()
        args, kwargs = mock_list.call_args
        status_arg = kwargs.get("status") or (args[1] if len(args) > 1 else None)
        assert str(status_arg) == "PENDING"

    def test_filter_by_reached_out_status(self, auth_client, sample_lead_dict_reached_out):
        with patch(
            "app.repositories.lead_repository.list_leads",
            return_value=[sample_lead_dict_reached_out],
        ) as mock_list:
            auth_client.get(f"{LEADS_URL}?status=REACHED_OUT")
        mock_list.assert_called_once()

    def test_no_status_filter_calls_list_with_none(self, auth_client, sample_lead_dict):
        with patch(
            "app.repositories.lead_repository.list_leads",
            return_value=[sample_lead_dict],
        ) as mock_list:
            auth_client.get(LEADS_URL)
        args, kwargs = mock_list.call_args
        status_arg = kwargs.get("status") or (args[1] if len(args) > 1 else None)
        assert status_arg is None

    def test_empty_list_returns_200_with_empty_array(self, auth_client):
        with patch("app.repositories.lead_repository.list_leads", return_value=[]):
            response = auth_client.get(LEADS_URL)
        assert response.status_code == 200
        assert response.json() == []

    def test_invalid_status_filter_returns_422(self, auth_client):
        response = auth_client.get(f"{LEADS_URL}?status=INVALID")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/leads/{id} — detail
# ---------------------------------------------------------------------------

class TestGetLead:
    def test_no_auth_returns_401(self, client, sample_lead_dict):
        lead_id = sample_lead_dict["id"]
        response = client.get(f"{LEADS_URL}/{lead_id}")
        assert response.status_code == 401

    def test_authenticated_found_returns_200(self, auth_client, sample_lead_dict):
        lead_id = sample_lead_dict["id"]
        with (
            patch("app.repositories.lead_repository.get_lead_by_id", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
        ):
            response = auth_client.get(f"{LEADS_URL}/{lead_id}")
        assert response.status_code == 200

    def test_not_found_returns_404(self, auth_client):
        from app.exceptions import LeadNotFoundError
        with patch(
            "app.repositories.lead_repository.get_lead_by_id",
            return_value=None,
        ):
            response = auth_client.get(f"{LEADS_URL}/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_response_contains_resume_url(self, auth_client, sample_lead_dict):
        lead_id = sample_lead_dict["id"]
        with (
            patch("app.repositories.lead_repository.get_lead_by_id", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
        ):
            response = auth_client.get(f"{LEADS_URL}/{lead_id}")
        assert response.json()["resume_url"] == PRESIGNED_URL

    def test_mints_fresh_presigned_url_on_each_get(self, auth_client, sample_lead_dict):
        """create_presigned_url must be called on every GET /api/leads/{id}."""
        lead_id = sample_lead_dict["id"]
        with (
            patch("app.repositories.lead_repository.get_lead_by_id", return_value=sample_lead_dict),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL) as mock_presign,
        ):
            auth_client.get(f"{LEADS_URL}/{lead_id}")
            auth_client.get(f"{LEADS_URL}/{lead_id}")
        assert mock_presign.call_count == 2

    def test_lead_without_resume_returns_null_resume_url(self, auth_client, sample_lead_dict_no_resume):
        lead_id = sample_lead_dict_no_resume["id"]
        with patch(
            "app.repositories.lead_repository.get_lead_by_id",
            return_value=sample_lead_dict_no_resume,
        ):
            response = auth_client.get(f"{LEADS_URL}/{lead_id}")
        assert response.json()["resume_url"] is None

    def test_invalid_uuid_returns_422(self, auth_client):
        response = auth_client.get(f"{LEADS_URL}/not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/leads/{id}/status — state transition
# ---------------------------------------------------------------------------

class TestUpdateLeadStatus:
    def test_no_auth_returns_401(self, client, sample_lead_dict):
        lead_id = sample_lead_dict["id"]
        response = client.patch(
            f"{LEADS_URL}/{lead_id}/status",
            json={"status": "REACHED_OUT"},
        )
        assert response.status_code == 401

    def test_pending_to_reached_out_returns_200(self, auth_client, sample_lead_dict, sample_lead_dict_reached_out):
        lead_id = sample_lead_dict["id"]
        with (
            patch("app.repositories.lead_repository.get_lead_by_id", return_value=sample_lead_dict),
            patch("app.repositories.lead_repository.update_status", return_value=sample_lead_dict_reached_out),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
        ):
            response = auth_client.patch(
                f"{LEADS_URL}/{lead_id}/status",
                json={"status": "REACHED_OUT"},
            )
        assert response.status_code == 200

    def test_response_status_is_reached_out(self, auth_client, sample_lead_dict, sample_lead_dict_reached_out):
        lead_id = sample_lead_dict["id"]
        with (
            patch("app.repositories.lead_repository.get_lead_by_id", return_value=sample_lead_dict),
            patch("app.repositories.lead_repository.update_status", return_value=sample_lead_dict_reached_out),
            patch("app.services.storage_service.create_presigned_url", return_value=PRESIGNED_URL),
        ):
            response = auth_client.patch(
                f"{LEADS_URL}/{lead_id}/status",
                json={"status": "REACHED_OUT"},
            )
        assert response.json()["status"] == "REACHED_OUT"

    def test_already_reached_out_returns_409(self, auth_client, sample_lead_dict_reached_out):
        lead_id = sample_lead_dict_reached_out["id"]
        with patch(
            "app.repositories.lead_repository.get_lead_by_id",
            return_value=sample_lead_dict_reached_out,
        ):
            response = auth_client.patch(
                f"{LEADS_URL}/{lead_id}/status",
                json={"status": "REACHED_OUT"},
            )
        assert response.status_code == 409

    def test_lead_not_found_returns_404(self, auth_client):
        with patch(
            "app.repositories.lead_repository.get_lead_by_id",
            return_value=None,
        ):
            response = auth_client.patch(
                f"{LEADS_URL}/{uuid.uuid4()}/status",
                json={"status": "REACHED_OUT"},
            )
        assert response.status_code == 404

    def test_invalid_status_value_returns_422(self, auth_client, sample_lead_dict):
        lead_id = sample_lead_dict["id"]
        response = auth_client.patch(
            f"{LEADS_URL}/{lead_id}/status",
            json={"status": "INVALID"},
        )
        assert response.status_code == 422

    def test_missing_status_field_returns_422(self, auth_client, sample_lead_dict):
        lead_id = sample_lead_dict["id"]
        response = auth_client.patch(f"{LEADS_URL}/{lead_id}/status", json={})
        assert response.status_code == 422

    def test_update_status_not_called_when_transition_illegal(
        self, auth_client, sample_lead_dict_reached_out
    ):
        lead_id = sample_lead_dict_reached_out["id"]
        with (
            patch(
                "app.repositories.lead_repository.get_lead_by_id",
                return_value=sample_lead_dict_reached_out,
            ),
            patch("app.repositories.lead_repository.update_status") as mock_update,
        ):
            auth_client.patch(
                f"{LEADS_URL}/{lead_id}/status",
                json={"status": "REACHED_OUT"},
            )
        mock_update.assert_not_called()

    def test_response_includes_fresh_presigned_url(
        self, auth_client, sample_lead_dict, sample_lead_dict_reached_out
    ):
        lead_id = sample_lead_dict["id"]
        fresh_url = "http://localhost:9000/resumes/fresh-url?X-Amz-Signature=fresh"
        with (
            patch("app.repositories.lead_repository.get_lead_by_id", return_value=sample_lead_dict),
            patch("app.repositories.lead_repository.update_status", return_value=sample_lead_dict_reached_out),
            patch("app.services.storage_service.create_presigned_url", return_value=fresh_url),
        ):
            response = auth_client.patch(
                f"{LEADS_URL}/{lead_id}/status",
                json={"status": "REACHED_OUT"},
            )
        assert response.json()["resume_url"] == fresh_url
