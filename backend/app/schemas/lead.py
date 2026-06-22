from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, field_validator

from app.models.lead import LeadStatus


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("cannot be empty or whitespace")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class LeadOut(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    status: LeadStatus
    status_updated_at: datetime
    created_at: datetime
    resume_filename: str | None
    resume_url: str | None


class LeadListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    status: LeadStatus
    created_at: datetime
    status_updated_at: datetime


class StatusUpdateIn(BaseModel):
    status: LeadStatus


class ErrorResponse(BaseModel):
    detail: str
