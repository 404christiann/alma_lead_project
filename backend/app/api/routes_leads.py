import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.deps import get_current_attorney
from app.config import get_settings
from app.db import get_db_conn
from app.exceptions import IllegalTransitionError, LeadNotFoundError, StorageError
from app.models.lead import LeadStatus, can_transition
from app.repositories import lead_repository
from app.schemas.lead import LeadCreate, LeadListItem, LeadOut, StatusUpdateIn
from app.services import email_service, file_validator, storage_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_lead_out(lead_dict: dict, resume_url: str | None) -> LeadOut:
    return LeadOut(
        id=lead_dict["id"],
        first_name=lead_dict["first_name"],
        last_name=lead_dict["last_name"],
        email=lead_dict["email"],
        status=lead_dict["status"],
        status_updated_at=lead_dict["status_updated_at"],
        created_at=lead_dict["created_at"],
        resume_filename=lead_dict.get("resume_filename"),
        resume_url=resume_url,
    )


def _mint_presigned_url(lead_dict: dict) -> str | None:
    if not lead_dict.get("resume_path"):
        return None
    settings = get_settings()
    s3 = storage_service.get_presign_client(settings)
    return storage_service.create_presigned_url(
        s3, settings.MINIO_BUCKET, lead_dict["resume_path"], settings.PRESIGNED_URL_TTL_SECONDS
    )


@router.post("/api/leads", status_code=201, response_model=LeadOut)
async def create_lead(
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
    conn=Depends(get_db_conn),
) -> LeadOut:
    settings = get_settings()
    data = await resume.read()

    if not resume.filename:
        from app.exceptions import FileValidationError
        raise FileValidationError("Resume filename is missing")

    ext, sniffed_mime = file_validator.validate_resume(
        resume.filename, resume.content_type, data, settings.MAX_FILE_BYTES
    )

    lead_data = LeadCreate(first_name=first_name, last_name=last_name, email=email)
    lead_dict = lead_repository.insert_lead(conn, lead_data)
    lead_id = lead_dict["id"]

    s3_upload = storage_service.get_upload_client(settings)
    try:
        path = storage_service.upload_resume(
            s3_upload, settings.MINIO_BUCKET, lead_id, resume.filename, data, sniffed_mime
        )
    except StorageError:
        try:
            lead_repository.delete_lead(conn, lead_id)
        except Exception as comp_exc:
            logger.warning("Compensation delete_lead failed for lead %s: %s", lead_id, comp_exc)
        raise

    try:
        lead_dict = lead_repository.update_resume_info(
            conn, lead_id, path, resume.filename, sniffed_mime
        )
    except Exception as exc:
        try:
            storage_service.delete_object(s3_upload, settings.MINIO_BUCKET, path)
            lead_repository.delete_lead(conn, lead_id)
        except Exception as comp_exc:
            logger.warning("Compensation failed for lead %s: %s", lead_id, comp_exc)
        raise StorageError("Failed to save resume metadata") from exc

    s3_presign = storage_service.get_presign_client(settings)
    resume_url = storage_service.create_presigned_url(
        s3_presign, settings.MINIO_BUCKET, path, settings.PRESIGNED_URL_TTL_SECONDS
    )

    email_service.send_prospect_confirmation(lead_data.email, lead_data.first_name)
    email_service.send_attorney_notification(settings.ATTORNEY_EMAIL, _build_lead_out(lead_dict, resume_url))

    return _build_lead_out(lead_dict, resume_url)


@router.get("/api/leads", response_model=list[LeadListItem])
async def list_leads_route(
    status: LeadStatus | None = Query(None),
    attorney: dict = Depends(get_current_attorney),
    conn=Depends(get_db_conn),
) -> list[LeadListItem]:
    leads = lead_repository.list_leads(conn, status=status)
    return [LeadListItem(**lead) for lead in leads]


@router.get("/api/leads/{lead_id}", response_model=LeadOut)
async def get_lead_route(
    lead_id: UUID,
    attorney: dict = Depends(get_current_attorney),
    conn=Depends(get_db_conn),
) -> LeadOut:
    lead_dict = lead_repository.get_lead_by_id(conn, lead_id)
    if lead_dict is None:
        raise LeadNotFoundError("Lead not found")
    return _build_lead_out(lead_dict, _mint_presigned_url(lead_dict))


@router.patch("/api/leads/{lead_id}/status", response_model=LeadOut)
async def update_status_route(
    lead_id: UUID,
    body: StatusUpdateIn,
    attorney: dict = Depends(get_current_attorney),
    conn=Depends(get_db_conn),
) -> LeadOut:
    lead_dict = lead_repository.get_lead_by_id(conn, lead_id)
    if lead_dict is None:
        raise LeadNotFoundError("Lead not found")

    current_status = LeadStatus(lead_dict["status"])
    if not can_transition(current_status, body.status):
        raise IllegalTransitionError("Transition not allowed")

    updated = lead_repository.update_status(conn, lead_id, body.status)
    return _build_lead_out(updated, _mint_presigned_url(updated))
