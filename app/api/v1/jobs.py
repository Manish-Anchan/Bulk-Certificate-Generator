from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import Job
from app.models.recipient import Recipient, RecipientStatus
from app.schemas.job import JobAcceptedResponse, JobCreate, JobDetailResponse
from app.schemas.recipient import RecipientResponse
from app.services.job_service import job_service
from app.services.storage_service import storage_service

router = APIRouter()


@router.post(
    "",
    response_model=JobAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Bulk Certificate Generation Request",
    description="Accepts a batch of recipients and event metadata, validates input, initializes the job, and enqueues background PDF generation.",
)
async def create_generation_job(
    job_in: JobCreate,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JobAcceptedResponse:
    """Ingest bulk certificate generation request and run asynchronously."""
    # 1. Create Job and Recipient records in DB
    job = await job_service.create_job(job_in, db)

    # 2. Enqueue background processing
    background_tasks.add_task(job_service.process_job, job.id)

    # 3. Return 202 Accepted immediately
    return JobAcceptedResponse(
        job_id=job.id,
        status=job.status,
        total_recipients=job.total_recipients,
        message="Certificate generation job accepted and enqueued.",
        status_url=f"/api/v1/jobs/{job.id}",
    )


@router.get(
    "/{job_id}",
    response_model=JobDetailResponse,
    summary="Get Job Status and Progress",
    description="Poll real-time progress, statistics, and individual recipient generation statuses.",
)
async def get_job_status(
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=1000, description="Pagination limit"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    status_filter: str | None = Query(
        default=None,
        description="Filter recipients by status: SUCCESS, FAILED, PENDING, or ALL",
    ),
) -> JobDetailResponse:
    """Retrieve job metadata, execution metrics, and itemized recipient outcomes."""
    job_data = await job_service.get_job_with_recipients(
        job_id=job_id,
        db=db,
        limit=limit,
        offset=offset,
        status_filter=status_filter,
    )
    if not job_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate job with ID '{job_id}' not found.",
        )

    job, recipients = job_data

    # Build recipient responses with download URLs
    recipients_out: list[RecipientResponse] = []
    for r in recipients:
        rec_data = RecipientResponse(
            id=r.id,
            recipient_name=r.recipient_name,
            recipient_email=r.recipient_email,
            status=r.status,
            certificate_id=r.certificate_id,
            download_url=(
                f"/api/v1/certificates/{r.certificate_id}/download"
                if r.status == RecipientStatus.SUCCESS and r.certificate_id
                else None
            ),
            error_message=r.error_message,
            generated_at=r.generated_at,
            custom_fields=r.custom_fields,
        )
        recipients_out.append(rec_data)

    zip_url = f"/api/v1/jobs/{job.id}/download" if job.success_count > 0 else None

    return JobDetailResponse(
        job_id=job.id,

        event_name=job.event_name,
        issuer_name=job.issuer_name,
        certificate_title=job.certificate_title,
        issue_date=job.issue_date,
        status=job.status,
        total_recipients=job.total_recipients,
        processed_count=job.processed_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        progress_percentage=job.progress_percentage,
        created_at=job.created_at,
        completed_at=job.completed_at,
        zip_download_url=zip_url,
        recipients=recipients_out,
    )


@router.get(
    "/{job_id}/download",
    summary="Download All Certificates (ZIP Archive)",
    description="Package and stream all successfully generated certificates for a job as a single .zip file.",
)
async def download_job_certificates_zip(
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate and stream a zip archive containing all generated certificates for this job."""
    # Verify job existence
    stmt = select(Job).where(Job.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate job with ID '{job_id}' not found.",
        )

    # Fetch successful recipients
    stmt_rec = select(Recipient).where(
        Recipient.job_id == job_id,
        Recipient.status == RecipientStatus.SUCCESS,
    )
    rec_result = await db.execute(stmt_rec)
    successful_recipients = list(rec_result.scalars().all())

    if not successful_recipients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No certificates have been successfully generated for this job yet.",
        )

    # Prepare file mappings (sanitize display name)
    files_to_zip = []
    for r in successful_recipients:
        if r.certificate_file_path and storage_service.certificate_exists(r.certificate_file_path):
            safe_name = "".join(c for c in r.recipient_name if c.isalnum() or c in (" ", "_", "-")).strip()
            display_filename = f"{safe_name}_{r.certificate_id}.pdf"
            files_to_zip.append((display_filename, r.certificate_file_path))

    if not files_to_zip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generated certificate files could not be located on disk.",
        )

    zip_path = storage_service.create_job_zip(job_id, files_to_zip)

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"certificates_{job.id}.zip",
    )
