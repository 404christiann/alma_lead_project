from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.api import routes_auth, routes_leads
from app.config import get_settings
from app.exceptions import (
    DuplicateLeadError,
    FileValidationError,
    IllegalTransitionError,
    InvalidCredentialsError,
    LeadNotFoundError,
    StorageError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app import db
    from app.services import storage_service

    db.init_pool()

    settings = get_settings()
    s3 = storage_service.get_upload_client(settings)
    storage_service.ensure_bucket(s3, settings.MINIO_BUCKET)

    yield


app = FastAPI(lifespan=lifespan)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router)
app.include_router(routes_leads.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(DuplicateLeadError)
async def handle_duplicate_lead(request: Request, exc: DuplicateLeadError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(FileValidationError)
async def handle_file_validation(request: Request, exc: FileValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(IllegalTransitionError)
async def handle_illegal_transition(request: Request, exc: IllegalTransitionError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(LeadNotFoundError)
async def handle_lead_not_found(request: Request, exc: LeadNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(StorageError)
async def handle_storage_error(request: Request, exc: StorageError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(InvalidCredentialsError)
async def handle_invalid_credentials(request: Request, exc: InvalidCredentialsError):
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(PydanticValidationError)
async def handle_pydantic_validation(request: Request, exc: PydanticValidationError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})
