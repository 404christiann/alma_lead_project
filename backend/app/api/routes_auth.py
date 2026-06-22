import bcrypt
from fastapi import APIRouter, Depends

from app.api.deps import get_current_attorney
from app.db import get_db_conn
from app.exceptions import InvalidCredentialsError
from app.repositories import attorney_repository
from app.schemas.auth import LoginIn, TokenOut
from app.services import auth_service

router = APIRouter()


@router.post("/api/auth/login", response_model=TokenOut)
async def login(body: LoginIn, conn=Depends(get_db_conn)) -> TokenOut:
    attorney = attorney_repository.get_by_email(conn, body.email)
    if attorney is None:
        raise InvalidCredentialsError("Invalid credentials")
    if not bcrypt.checkpw(body.password.encode(), attorney["password_hash"].encode()):
        raise InvalidCredentialsError("Invalid credentials")
    token = auth_service.create_access_token(attorney["id"], attorney["email"])
    return TokenOut(access_token=token)
