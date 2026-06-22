from enum import Enum


class LeadStatus(str, Enum):
    PENDING = "PENDING"
    REACHED_OUT = "REACHED_OUT"

    def __str__(self) -> str:
        return self.value


ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg",
})

EXTENSION_TO_MIME: dict[str, frozenset[str]] = {
    ".pdf":  frozenset({"application/pdf"}),
    ".png":  frozenset({"image/png"}),
    ".jpg":  frozenset({"image/jpeg"}),
    ".jpeg": frozenset({"image/jpeg"}),
    ".doc":  frozenset({"application/msword", "application/x-ole-storage"}),
    ".docx": frozenset({
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/x-zip",
        "application/x-zip-compressed",
    }),
}

ALLOWED_MIME_TYPES: frozenset[str] = frozenset().union(*EXTENSION_TO_MIME.values())


def can_transition(current: LeadStatus, target: LeadStatus) -> bool:
    return current == LeadStatus.PENDING and target == LeadStatus.REACHED_OUT
