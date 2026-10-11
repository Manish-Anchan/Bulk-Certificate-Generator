from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.recipient import Recipient, RecipientStatus
from app.schemas.job import CertificateVerifyResponse
from app.schemas.recipient import RecipientResponse
from app.services.storage_service import storage_service

router = APIRouter()


@router.get(
    "/{certificate_id}/download",
    summary="Download Individual Certificate PDF",
    description="Stream the generated PDF certificate for a recipient by certificate ID.",
)
async def download_certificate(
    certificate_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve and stream an individual certificate PDF."""
    stmt = select(Recipient).where(Recipient.certificate_id == certificate_id)
    result = await db.execute(stmt)
    recipient = result.scalar_one_or_none()

    if not recipient or recipient.status != RecipientStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found or not yet generated.",
        )

    if not recipient.certificate_file_path or not storage_service.certificate_exists(
        recipient.certificate_file_path
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate PDF file not found on disk.",
        )

    safe_name = "".join(
        c for c in recipient.recipient_name if c.isalnum() or c in (" ", "_", "-")
    ).strip()
    download_filename = f"{safe_name}_{certificate_id}.pdf"

    return FileResponse(
        path=recipient.certificate_file_path,
        media_type="application/pdf",
        filename=download_filename,
    )


@router.get(
    "/{certificate_id}/verify",
    response_model=CertificateVerifyResponse,
    summary="Verify Certificate Authenticity",
    description="Public endpoint to verify the validity of a certificate using its credential ID.",
)
async def verify_certificate(
    certificate_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CertificateVerifyResponse:
    """Verify that a certificate is genuine and return its issue details."""
    stmt = (
        select(Recipient)
        .options(selectinload(Recipient.job))
        .where(Recipient.certificate_id == certificate_id)
    )
    result = await db.execute(stmt)
    recipient = result.scalar_one_or_none()

    if (
        not recipient
        or recipient.status != RecipientStatus.SUCCESS
        or not recipient.job
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' could not be verified.",
        )

    return CertificateVerifyResponse(
        valid=True,
        certificate_id=recipient.certificate_id,
        recipient_name=recipient.recipient_name,
        event_name=recipient.job.event_name,
        issuer_name=recipient.job.issuer_name,
        certificate_title=recipient.job.certificate_title,
        issue_date=recipient.job.issue_date,
        issued_at=recipient.generated_at,
        verification_message="Certificate is authentic and officially recognized.",
    )


@router.get(
    "/{certificate_id}",
    response_model=RecipientResponse,
    summary="Get Certificate Metadata",
    description="Retrieve recipient and certificate metadata by certificate ID.",
)
async def get_certificate_metadata(
    certificate_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecipientResponse:
    """Get metadata for a specific certificate."""
    stmt = select(Recipient).where(Recipient.certificate_id == certificate_id)
    result = await db.execute(stmt)
    recipient = result.scalar_one_or_none()

    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found.",
        )

    return RecipientResponse(
        id=recipient.id,
        recipient_name=recipient.recipient_name,
        recipient_email=recipient.recipient_email,
        status=recipient.status,
        certificate_id=recipient.certificate_id,
        download_url=(
            f"/api/v1/certificates/{recipient.certificate_id}/download"
            if recipient.status == RecipientStatus.SUCCESS and recipient.certificate_id
            else None
        ),
        error_message=recipient.error_message,
        generated_at=recipient.generated_at,
        custom_fields=recipient.custom_fields,
    )
