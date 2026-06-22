"""
Tests for app/models/lead.py

Covers: LeadStatus enum values, can_transition rules, ALLOWED_EXTENSIONS,
ALLOWED_MIME_TYPES, EXTENSION_TO_MIME completeness.
"""
import pytest
from app.models.lead import (
    LeadStatus,
    can_transition,
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    EXTENSION_TO_MIME,
)


class TestLeadStatus:
    def test_pending_value(self):
        assert LeadStatus.PENDING == "PENDING"

    def test_reached_out_value(self):
        assert LeadStatus.REACHED_OUT == "REACHED_OUT"

    def test_is_string_subclass(self):
        assert isinstance(LeadStatus.PENDING, str)
        assert isinstance(LeadStatus.REACHED_OUT, str)

    def test_only_two_states(self):
        assert len(LeadStatus) == 2


class TestCanTransition:
    def test_pending_to_reached_out_allowed(self):
        assert can_transition(LeadStatus.PENDING, LeadStatus.REACHED_OUT) is True

    def test_reached_out_to_pending_forbidden(self):
        assert can_transition(LeadStatus.REACHED_OUT, LeadStatus.PENDING) is False

    def test_pending_to_pending_forbidden(self):
        assert can_transition(LeadStatus.PENDING, LeadStatus.PENDING) is False

    def test_reached_out_to_reached_out_forbidden(self):
        assert can_transition(LeadStatus.REACHED_OUT, LeadStatus.REACHED_OUT) is False

    def test_returns_bool(self):
        result = can_transition(LeadStatus.PENDING, LeadStatus.REACHED_OUT)
        assert isinstance(result, bool)


class TestAllowedExtensions:
    def test_pdf_allowed(self):
        assert ".pdf" in ALLOWED_EXTENSIONS

    def test_doc_allowed(self):
        assert ".doc" in ALLOWED_EXTENSIONS

    def test_docx_allowed(self):
        assert ".docx" in ALLOWED_EXTENSIONS

    def test_png_allowed(self):
        assert ".png" in ALLOWED_EXTENSIONS

    def test_jpg_allowed(self):
        assert ".jpg" in ALLOWED_EXTENSIONS

    def test_jpeg_allowed(self):
        assert ".jpeg" in ALLOWED_EXTENSIONS

    def test_exe_not_allowed(self):
        assert ".exe" not in ALLOWED_EXTENSIONS

    def test_py_not_allowed(self):
        assert ".py" not in ALLOWED_EXTENSIONS

    def test_sh_not_allowed(self):
        assert ".sh" not in ALLOWED_EXTENSIONS

    def test_zip_not_allowed(self):
        assert ".zip" not in ALLOWED_EXTENSIONS

    def test_is_frozenset(self):
        assert isinstance(ALLOWED_EXTENSIONS, frozenset)

    def test_extensions_are_lowercase_with_dot(self):
        for ext in ALLOWED_EXTENSIONS:
            assert ext.startswith("."), f"{ext!r} must start with '.'"
            assert ext == ext.lower(), f"{ext!r} must be lowercase"


class TestAllowedMimeTypes:
    def test_pdf_mime_allowed(self):
        assert "application/pdf" in ALLOWED_MIME_TYPES

    def test_png_mime_allowed(self):
        assert "image/png" in ALLOWED_MIME_TYPES

    def test_jpeg_mime_allowed(self):
        assert "image/jpeg" in ALLOWED_MIME_TYPES

    def test_is_frozenset(self):
        assert isinstance(ALLOWED_MIME_TYPES, frozenset)


class TestExtensionToMime:
    def test_every_allowed_extension_has_mapping(self):
        for ext in ALLOWED_EXTENSIONS:
            assert ext in EXTENSION_TO_MIME, f"Extension {ext!r} missing from EXTENSION_TO_MIME"

    def test_pdf_maps_to_pdf_mime(self):
        assert "application/pdf" in EXTENSION_TO_MIME[".pdf"]

    def test_png_maps_to_png_mime(self):
        assert "image/png" in EXTENSION_TO_MIME[".png"]

    def test_jpg_maps_to_jpeg_mime(self):
        assert "image/jpeg" in EXTENSION_TO_MIME[".jpg"]

    def test_jpeg_maps_to_jpeg_mime(self):
        assert "image/jpeg" in EXTENSION_TO_MIME[".jpeg"]

    def test_values_are_sets(self):
        for ext, mimes in EXTENSION_TO_MIME.items():
            assert isinstance(mimes, (set, frozenset)), f"{ext} value must be a set"
