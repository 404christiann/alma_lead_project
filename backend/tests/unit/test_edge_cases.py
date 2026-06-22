"""
Unit tests for edge cases not covered by the existing suite.
Ordered by likelihood of catching a real bug if the underlying code regresses.

1. LeadStatus.__str__ — Python 3.11 StrEnum gotcha. If the __str__ override is
   removed, str(LeadStatus.PENDING) returns "LeadStatus.PENDING" instead of
   "PENDING", silently breaking every status DB query and comparison.

2. validate_resume when filetype.guess() returns None — the unidentifiable-content
   branch (file_validator.py line 28-29) has no test. Any file whose bytes don't
   match a known signature hits this path; it must raise FileValidationError, not
   fall through to a MIME mismatch error with a misleading message.

3. validate_resume with .doc (OLE2) magic bytes — .doc is an ALLOWED_EXTENSION
   but has zero test coverage. The OLE2 magic bytes must survive the MIME cross-
   check against EXTENSION_TO_MIME[".doc"].
"""
import pytest

from app.exceptions import FileValidationError
from app.models.lead import LeadStatus, EXTENSION_TO_MIME
from app.services.file_validator import validate_resume

MAX_BYTES = 10 * 1024 * 1024

# OLE2 Compound Document magic — used by .doc, .xls, .ppt (old binary formats)
_OLE2_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 500


# ---------------------------------------------------------------------------
# 1. LeadStatus.__str__ — must return the value, not the qualified class name
# ---------------------------------------------------------------------------

class TestLeadStatusStrRepresentation:
    def test_str_pending_is_value_not_classname(self):
        assert str(LeadStatus.PENDING) == "PENDING"

    def test_str_reached_out_is_value_not_classname(self):
        assert str(LeadStatus.REACHED_OUT) == "REACHED_OUT"

    def test_str_pending_matches_enum_value(self):
        assert str(LeadStatus.PENDING) == LeadStatus.PENDING.value

    def test_str_reached_out_matches_enum_value(self):
        assert str(LeadStatus.REACHED_OUT) == LeadStatus.REACHED_OUT.value

    def test_status_embedded_in_query_string_contains_no_classname(self):
        """Regression guard: embedding status in a SQL fragment must not include 'LeadStatus.'"""
        fragment = f"WHERE status = '{LeadStatus.PENDING}'"
        assert "LeadStatus" not in fragment
        assert "PENDING" in fragment

    def test_f_string_interpolation_matches_db_value(self):
        """f-string interpolation calls __str__; result must match what the DB stores."""
        assert f"{LeadStatus.REACHED_OUT}" == "REACHED_OUT"


# ---------------------------------------------------------------------------
# 2. validate_resume — filetype.guess() returns None (unidentifiable content)
# ---------------------------------------------------------------------------

class TestValidateResumeUnidentifiableContent:
    def test_empty_bytes_raises_file_validation_error(self):
        """Empty file has no magic bytes; filetype.guess() returns None."""
        with pytest.raises(FileValidationError):
            validate_resume("resume.pdf", "application/pdf", b"", MAX_BYTES)

    def test_null_bytes_with_pdf_extension_raises(self):
        """All-zero bytes don't match any known magic signature."""
        with pytest.raises(FileValidationError):
            validate_resume("resume.pdf", "application/pdf", b"\x00" * 512, MAX_BYTES)

    def test_plain_text_with_pdf_extension_raises(self):
        """Plain text has no recognisable magic bytes — must not silently pass."""
        text = b"This is a resume. I have many skills." * 20
        with pytest.raises(FileValidationError):
            validate_resume("resume.pdf", "application/pdf", text, MAX_BYTES)

    def test_plain_text_with_docx_extension_raises(self):
        """Plain text with .docx extension must also fail, not produce wrong MIME."""
        text = b"Name: Jane Doe\nExperience: 5 years" * 20
        with pytest.raises(FileValidationError):
            validate_resume(
                "resume.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                text,
                MAX_BYTES,
            )


# ---------------------------------------------------------------------------
# 3. validate_resume — .doc (OLE2 Compound Document) magic bytes
# ---------------------------------------------------------------------------

class TestValidateResumeDocExtension:
    def test_ole2_magic_bytes_are_accepted_for_doc(self):
        """.doc files with OLE2 magic bytes must pass validation end-to-end."""
        ext, mime = validate_resume("resume.doc", "application/msword", _OLE2_MAGIC, MAX_BYTES)
        assert ext == ".doc"

    def test_doc_sniffed_mime_is_in_allowed_set(self):
        """Sniffed MIME for .doc must be one of the values declared in EXTENSION_TO_MIME."""
        _, mime = validate_resume("resume.doc", "application/msword", _OLE2_MAGIC, MAX_BYTES)
        assert mime in EXTENSION_TO_MIME[".doc"]

    def test_doc_extension_in_allowed_extensions(self):
        """Sanity check: .doc must be in the allow-list so the validator doesn't reject it first."""
        from app.models.lead import ALLOWED_EXTENSIONS
        assert ".doc" in ALLOWED_EXTENSIONS

    def test_doc_extension_with_jpg_bytes_raises(self):
        """.doc extension with JPEG magic bytes must fail the MIME cross-check."""
        jpg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 200
        with pytest.raises(FileValidationError):
            validate_resume("resume.doc", "application/msword", jpg_bytes, MAX_BYTES)

    def test_doc_extension_with_pdf_bytes_raises(self):
        """.doc extension with PDF magic bytes must fail the MIME cross-check."""
        pdf_bytes = b"%PDF-1.4 " + b"x" * 200
        with pytest.raises(FileValidationError):
            validate_resume("resume.doc", "application/msword", pdf_bytes, MAX_BYTES)
