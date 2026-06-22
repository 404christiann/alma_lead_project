from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import jwt

from app.config import get_settings


def create_access_token(attorney_id: UUID, email: str) -> str:
    settings = get_settings()
    payload = {
        "sub": str(attorney_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
