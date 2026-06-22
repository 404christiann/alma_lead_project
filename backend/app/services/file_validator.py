import os
import re

import filetype

from app.exceptions import FileValidationError
from app.models.lead import ALLOWED_EXTENSIONS, EXTENSION_TO_MIME

# OLE2 Compound Document magic — used by .doc, .xls, .ppt (old binary Office formats).
# filetype does not identify OLE2 containers, so we fall back to a manual check.
_OLE2_MAGIC = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
_OLE2_MIME = "application/msword"


def _sniff_mime(data: bytes) -> str | None:
    guessed = filetype.guess(data)
    if guessed is not None:
        return guessed.mime
    if data[:8] == _OLE2_MAGIC:
        return _OLE2_MIME
    return None


def validate_resume(
    filename: str,
    content_type: str,
    data: bytes,
    max_bytes: int,
) -> tuple[str, str]:
    if len(data) > max_bytes:
        raise FileValidationError("File exceeds maximum allowed size")

    _, raw_ext = os.path.splitext(filename)
    if not raw_ext:
        raise FileValidationError("File has no extension")

    ext = raw_ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise FileValidationError(f"Extension {ext!r} is not allowed")

    sniffed_mime = _sniff_mime(data)
    if sniffed_mime is None:
        raise FileValidationError("Could not determine file type from content")

    if sniffed_mime not in EXTENSION_TO_MIME[ext]:
        raise FileValidationError(
            f"File content ({sniffed_mime}) does not match extension {ext!r}"
        )

    return (ext, sniffed_mime)


def sanitize_filename(filename: str) -> str:
    name = filename.replace("/", "").replace("\\", "")
    stem, ext = os.path.splitext(name)
    stem = re.sub(r"\s+", "_", stem)
    max_stem = 255 - len(ext)
    stem = stem[:max_stem]
    return stem + ext
