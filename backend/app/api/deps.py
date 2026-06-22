from fastapi import Header, HTTPException
from jose import JWTError, jwt

from app.config import get_settings


async def get_current_attorney(authorization: str | None = Header(None)) -> dict:
    settings = get_settings()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    try:
        claims = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return claims
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
