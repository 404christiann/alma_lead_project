"""
Tests for app/services/file_validator.py

Covers: validate_resume happy paths, oversize, bad extension, MIME mismatch,
sanitize_filename contract (path separators, whitespace, max length, extension).
"""
import pytest

from app.exceptions import FileValidationError
from app.services.file_validator import validate_resume, sanitize_filename

MAX_BYTES = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# validate_resume — happy paths
# ---------------------------------------------------------------------------

class TestValidateResumeHappyPaths:
    def test_valid_pdf_returns_extension_and_sniffed_mime(self, pdf_bytes):
        ext, mime = validate_resume("resume.pdf", "application/pdf", pdf_bytes, MAX_BYTES)
        assert ext == ".pdf"
        assert mime == "application/pdf"

    def test_valid_png_accepted(self, png_bytes):
        ext, mime = validate_resume("photo.png", "image/png", png_bytes, MAX_BYTES)
        assert ext == ".png"
        assert mime == "image/png"

    def test_valid_jpg_accepted(self, jpg_bytes):
        ext, mime = validate_resume("photo.jpg", "image/jpeg", jpg_bytes, MAX_BYTES)
        assert ext == ".jpg"
        assert mime == "image/jpeg"

    def test_valid_jpeg_extension_accepted(self, jpg_bytes):
        ext, mime = validate_resume("photo.jpeg", "image/jpeg", jpg_bytes, MAX_BYTES)
        assert ext == ".jpeg"

    def test_valid_docx_accepted(self, docx_bytes):
        ext, mime = validate_resume(
            "resume.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            docx_bytes,
            MAX_BYTES,
        )
        assert ext == ".docx"

    def test_returns_two_strings(self, pdf_bytes):
        result = validate_resume("resume.pdf", "application/pdf", pdf_bytes, MAX_BYTES)
        assert len(result) == 2
        assert all(isinstance(v, str) for v in result)

    def test_exactly_at_max_size_is_accepted(self, pdf_bytes):
        # Pad to exactly MAX_BYTES
        data = pdf_bytes + b"x" * (MAX_BYTES - len(pdf_bytes))
        ext, _ = validate_resume("resume.pdf", "application/pdf", data, MAX_BYTES)
        assert ext == ".pdf"

    def test_uppercase_extension_normalised(self, pdf_bytes):
        # ".PDF" should be treated the same as ".pdf"
        ext, mime = validate_resume("RESUME.PDF", "application/pdf", pdf_bytes, MAX_BYTES)
        assert ext.lower() == ".pdf"


# ---------------------------------------------------------------------------
# validate_resume — failure modes
# ---------------------------------------------------------------------------

class TestValidateResumeFailures:
    def test_oversize_raises_file_validation_error(self, oversize_bytes):
        with pytest.raises(FileValidationError):
            validate_resume("resume.pdf", "application/pdf", oversize_bytes, MAX_BYTES)

    def test_one_byte_over_max_raises(self, pdf_bytes):
        tight_limit = len(pdf_bytes) - 1
        with pytest.raises(FileValidationError):
            validate_resume("resume.pdf", "application/pdf", pdf_bytes, tight_limit)

    def test_disallowed_extension_exe_raises(self, exe_bytes):
        with pytest.raises(FileValidationError):
            validate_resume("malware.exe", "application/octet-stream", exe_bytes, MAX_BYTES)

    def test_disallowed_extension_py_raises(self, pdf_bytes):
        with pytest.raises(FileValidationError):
            validate_resume("script.py", "text/x-python", pdf_bytes, MAX_BYTES)

    def test_disallowed_extension_sh_raises(self, pdf_bytes):
        with pytest.raises(FileValidationError):
            validate_resume("setup.sh", "text/x-shellscript", pdf_bytes, MAX_BYTES)

    def test_no_extension_raises(self, pdf_bytes):
        with pytest.raises(FileValidationError):
            validate_resume("resume", "application/pdf", pdf_bytes, MAX_BYTES)

    def test_mime_mismatch_jpg_bytes_with_pdf_extension_raises(self, jpg_bytes):
        # JPEG magic bytes declared as .pdf → mismatch
        with pytest.raises(FileValidationError):
            validate_resume("resume.pdf", "application/pdf", jpg_bytes, MAX_BYTES)

    def test_mime_mismatch_pdf_bytes_with_png_extension_raises(self, pdf_bytes):
        with pytest.raises(FileValidationError):
            validate_resume("photo.png", "image/png", pdf_bytes, MAX_BYTES)

    def test_raises_file_validation_error_not_generic(self, oversize_bytes):
        with pytest.raises(FileValidationError):
            validate_resume("resume.pdf", "application/pdf", oversize_bytes, MAX_BYTES)

    def test_empty_filename_raises(self, pdf_bytes):
        with pytest.raises(FileValidationError):
            validate_resume("", "application/pdf", pdf_bytes, MAX_BYTES)


# ---------------------------------------------------------------------------
# sanitize_filename
# ---------------------------------------------------------------------------

class TestSanitizeFilename:
    def test_strips_forward_slashes(self):
        result = sanitize_filename("../../etc/passwd.pdf")
        assert "/" not in result

    def test_strips_backslashes(self):
        result = sanitize_filename("..\\windows\\system32.pdf")
        assert "\\" not in result

    def test_replaces_spaces_with_underscore(self):
        result = sanitize_filename("my resume file.pdf")
        assert " " not in result
        assert "_" in result

    def test_preserves_extension(self):
        result = sanitize_filename("my_resume.pdf")
        assert result.endswith(".pdf")

    def test_max_255_chars(self):
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_max_length_preserves_extension(self):
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert result.endswith(".pdf")

    def test_normal_filename_returns_nonempty(self):
        result = sanitize_filename("resume.pdf")
        assert len(result) > 0

    def test_collapses_multiple_spaces(self):
        result = sanitize_filename("my   resume.pdf")
        assert "  " not in result

    def test_result_is_string(self):
        assert isinstance(sanitize_filename("resume.pdf"), str)
