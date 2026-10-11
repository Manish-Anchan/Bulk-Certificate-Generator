from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.job import JobStatus
from app.schemas.recipient import RecipientCreate, RecipientResponse


class JobCreate(BaseModel):
    """Payload to request bulk certificate generation."""

    event_name: str = Field(
        ..., min_length=1, max_length=255, description="Name of the course/event"
    )
    issuer_name: str = Field(
        ..., min_length=1, max_length=255, description="Name of issuing authority"
    )
    certificate_title: str = Field(
        default="Certificate of Completion",
        min_length=1,
        max_length=255,
        description="Title of the certificate",
    )
    issue_date: date = Field(
        default_factory=date.today, description="Issue date on the certificate"
    )
    recipients: list[RecipientCreate] = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="List of recipients to generate certificates for (1-5000)",
    )

    @field_validator("event_name", "issuer_name", "certificate_title")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Field cannot be empty or whitespace only")
        return clean


class JobAcceptedResponse(BaseModel):
    """Response returned immediately upon accepting a job (202 Accepted)."""

    job_id: str
    status: JobStatus
    total_recipients: int
    message: str
    status_url: str


class JobDetailResponse(BaseModel):
    """Detailed job status and progress response."""

    job_id: str
    event_name: str
    issuer_name: str
    certificate_title: str
    issue_date: date
    status: JobStatus
    total_recipients: int
    processed_count: int
    success_count: int
    failed_count: int
    progress_percentage: float
    created_at: datetime
    completed_at: datetime | None = None
    zip_download_url: str | None = None
    recipients: list[RecipientResponse] = []

    model_config = ConfigDict(from_attributes=True)


class CertificateVerifyResponse(BaseModel):
    """Response for public certificate verification."""

    valid: bool
    certificate_id: str
    recipient_name: str
    event_name: str
    issuer_name: str
    certificate_title: str
    issue_date: date
    issued_at: datetime | None = None
    verification_message: str
