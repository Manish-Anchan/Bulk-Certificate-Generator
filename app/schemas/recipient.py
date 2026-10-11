import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.recipient import RecipientStatus

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class RecipientCreate(BaseModel):
    """Schema for recipient input in bulk certificate request."""

    name: str = Field(
        ..., min_length=1, max_length=200, description="Full name of recipient"
    )
    email: str = Field(
        ..., min_length=3, max_length=255, description="Email address of recipient"
    )
    custom_fields: dict[str, Any] | None = Field(
        default=None, description="Optional metadata"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Recipient name cannot be empty or whitespace only")
        return clean

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email format: '{v}'")
        return clean


class RecipientResponse(BaseModel):
    """Schema for recipient output details."""

    id: str
    recipient_name: str
    recipient_email: str
    status: RecipientStatus
    certificate_id: str | None = None
    download_url: str | None = None
    error_message: str | None = None
    generated_at: datetime | None = None
    custom_fields: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)
