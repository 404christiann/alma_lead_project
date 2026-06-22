"""
Tests for app/services/storage_service.py (pure / mockable parts)

Covers: sanitize_filename contract, create_presigned_url host verification
(the load-bearing SigV4 dual-client requirement), upload_resume raises
StorageError on S3 failure, delete_object never raises.
"""
import uuid
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

import pytest

from app.exceptions import StorageError
from app.services.storage_service import (
    sanitize_filename,
    create_presigned_url,
    upload_resume,
    delete_object,
)

BUCKET = "resumes"
LEAD_ID = uuid.uuid4()
OBJECT_PATH = f"resumes/{LEAD_ID}/resume.pdf"
PRESIGNED_URL = f"http://localhost:9000/{BUCKET}/{LEAD_ID}/resume.pdf?X-Amz-Signature=abc123"


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_strips_forward_slash(self):
        result = sanitize_filename("../../etc/passwd.pdf")
        assert "/" not in result

    def test_strips_backslash(self):
        result = sanitize_filename("..\\windows\\file.pdf")
        assert "\\" not in result

    def test_replaces_spaces_with_underscore(self):
        result = sanitize_filename("my resume.pdf")
        assert " " not in result
        assert "_" in result

    def test_preserves_extension(self):
        result = sanitize_filename("resume.pdf")
        assert result.endswith(".pdf")

    def test_result_max_255_chars(self):
        result = sanitize_filename("a" * 300 + ".pdf")
        assert len(result) <= 255

    def test_max_length_extension_preserved(self):
        result = sanitize_filename("a" * 300 + ".docx")
        assert result.endswith(".docx")

    def test_returns_nonempty_string(self):
        result = sanitize_filename("resume.pdf")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# create_presigned_url — host must be MINIO_PUBLIC_URL (localhost:9000)
# ---------------------------------------------------------------------------

class TestCreatePresignedUrl:
    def test_returns_a_string(self):
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = PRESIGNED_URL
        result = create_presigned_url(mock_s3, BUCKET, OBJECT_PATH)
        assert isinstance(result, str)

    def test_calls_generate_presigned_url_with_get_object(self):
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = PRESIGNED_URL
        create_presigned_url(mock_s3, BUCKET, OBJECT_PATH, expires_in_seconds=3600)
        mock_s3.generate_presigned_url.assert_called_once()
        args, kwargs = mock_s3.generate_presigned_url.call_args
        client_method = args[0] if args else kwargs.get("ClientMethod", "")
        assert client_method == "get_object"

    def test_url_host_is_localhost_9000(self):
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = PRESIGNED_URL
        url = create_presigned_url(mock_s3, BUCKET, OBJECT_PATH)
        parsed = urlparse(url)
        assert parsed.hostname == "localhost"
        assert parsed.port == 9000

    def test_url_is_not_internal_minio_host(self):
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = PRESIGNED_URL
        url = create_presigned_url(mock_s3, BUCKET, OBJECT_PATH)
        assert "minio:9000" not in url

    def test_passes_expiry_to_boto3(self):
        mock_s3 = MagicMock()
        mock_s3.generate_presigned_url.return_value = PRESIGNED_URL
        create_presigned_url(mock_s3, BUCKET, OBJECT_PATH, expires_in_seconds=1800)
        _, kwargs = mock_s3.generate_presigned_url.call_args
        expiry = kwargs.get("ExpiresIn") or (
            mock_s3.generate_presigned_url.call_args[1].get("ExpiresIn")
        )
        assert expiry == 1800


# ---------------------------------------------------------------------------
# upload_resume — raises StorageError on S3 failure
# ---------------------------------------------------------------------------

class TestUploadResume:
    def test_returns_object_key_string(self, pdf_bytes):
        mock_s3 = MagicMock()
        # put_object succeeds silently
        result = upload_resume(mock_s3, BUCKET, LEAD_ID, "resume.pdf", pdf_bytes, "application/pdf")
        assert isinstance(result, str)

    def test_object_key_contains_lead_id(self, pdf_bytes):
        mock_s3 = MagicMock()
        result = upload_resume(mock_s3, BUCKET, LEAD_ID, "resume.pdf", pdf_bytes, "application/pdf")
        assert str(LEAD_ID) in result

    def test_object_key_contains_filename(self, pdf_bytes):
        mock_s3 = MagicMock()
        result = upload_resume(mock_s3, BUCKET, LEAD_ID, "resume.pdf", pdf_bytes, "application/pdf")
        assert "resume" in result

    def test_raises_storage_error_on_s3_exception(self, pdf_bytes):
        mock_s3 = MagicMock()
        mock_s3.put_object.side_effect = Exception("S3 unreachable")
        with pytest.raises(StorageError):
            upload_resume(mock_s3, BUCKET, LEAD_ID, "resume.pdf", pdf_bytes, "application/pdf")

    def test_sanitizes_filename_in_key(self, pdf_bytes):
        mock_s3 = MagicMock()
        result = upload_resume(mock_s3, BUCKET, LEAD_ID, "my resume file.pdf", pdf_bytes, "application/pdf")
        assert " " not in result


# ---------------------------------------------------------------------------
# delete_object — never raises, logs failures
# ---------------------------------------------------------------------------

class TestDeleteObject:
    def test_succeeds_silently(self):
        mock_s3 = MagicMock()
        delete_object(mock_s3, BUCKET, OBJECT_PATH)  # must not raise

    def test_does_not_raise_on_s3_error(self):
        mock_s3 = MagicMock()
        mock_s3.delete_object.side_effect = Exception("S3 error")
        delete_object(mock_s3, BUCKET, OBJECT_PATH)  # must not raise

    def test_returns_none(self):
        mock_s3 = MagicMock()
        result = delete_object(mock_s3, BUCKET, OBJECT_PATH)
        assert result is None
