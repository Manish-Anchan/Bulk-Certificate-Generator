import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import database
from app.core.config import settings
from app.core.logging import logger
from app.models.job import Job, JobStatus
from app.models.recipient import Recipient, RecipientStatus
from app.schemas.job import JobCreate
from app.services.certificate_generator import certificate_generator
from app.services.storage_service import storage_service

# Dedicated thread pool for CPU-bound ReportLab rendering
thread_pool = ThreadPoolExecutor(max_workers=settings.MAX_WORKER_THREADS)


class JobService:
    """Service orchestrating batch certificate job ingestion, execution, and state tracking."""

    async def create_job(self, job_in: JobCreate, db: AsyncSession) -> Job:
        """Create a new certificate generation job and initialize all recipient rows."""
        job = Job(
            event_name=job_in.event_name,
            issuer_name=job_in.issuer_name,
            certificate_title=job_in.certificate_title,
            issue_date=job_in.issue_date,
            status=JobStatus.PENDING,
            total_recipients=len(job_in.recipients),
            processed_count=0,
            success_count=0,
            failed_count=0,
        )
        db.add(job)
        await db.flush()

        recipients = [
            Recipient(
                job_id=job.id,
                recipient_name=item.name,
                recipient_email=item.email,
                custom_fields=item.custom_fields,
                status=RecipientStatus.PENDING,
            )
            for item in job_in.recipients
        ]
        db.add_all(recipients)
        await db.commit()
        await db.refresh(job)

        logger.info(
            "Created Job %s with %d recipients for event '%s'",
            job.id,
            job.total_recipients,
            job.event_name,
        )
        return job

    async def get_job_with_recipients(
        self,
        job_id: str,
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        status_filter: str | None = None,
    ) -> tuple[Job, list[Recipient]] | None:
        """Fetch a job and its recipients with optional pagination and status filtering."""
        query = select(Job).where(Job.id == job_id)
        result = await db.execute(query)
        job = result.scalar_one_or_none()
        if not job:
            return None

        recipient_query = select(Recipient).where(Recipient.job_id == job_id)
        if status_filter and status_filter.upper() != "ALL":
            recipient_query = recipient_query.where(
                Recipient.status == RecipientStatus(status_filter.upper())
            )
        recipient_query = (
            recipient_query.order_by(Recipient.created_at).offset(offset).limit(limit)
        )

        rec_result = await db.execute(recipient_query)
        recipients = list(rec_result.scalars().all())
        return job, recipients

    def _render_certificate_sync(
        self,
        recipient_name: str,
        event_name: str,
        issuer_name: str,
        certificate_title: str,
        issue_date: date,
        certificate_id: str,
        output_path: str,
        verification_url: str,
    ) -> str:
        """Synchronous helper designed to execute within ThreadPoolExecutor."""
        certificate_generator.generate(
            recipient_name=recipient_name,
            event_name=event_name,
            issuer_name=issuer_name,
            certificate_title=certificate_title,
            issue_date=issue_date,
            certificate_id=certificate_id,
            output_path=output_path,
            verification_url=verification_url,
        )
        return output_path

    async def process_job(
        self, job_id: str, session: AsyncSession | None = None
    ) -> None:
        """Background worker method that processes all recipients with strict fault isolation."""
        if session is not None:
            await self._execute_job_processing(job_id, session)
        else:
            async with database.AsyncSessionLocal() as db_session:
                await self._execute_job_processing(job_id, db_session)

    async def _execute_job_processing(self, job_id: str, session: AsyncSession) -> None:
        """Internal execution loop for processing recipients and handling failures atomically."""
        try:
            # 1. Fetch Job and all its recipients
            stmt = (
                select(Job)
                .options(selectinload(Job.recipients))
                .where(Job.id == job_id)
            )
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                logger.error("Job %s not found for background processing", job_id)
                return

            # Idempotency guard: do not reprocess jobs that already reached terminal status
            if job.status in (
                JobStatus.COMPLETED,
                JobStatus.PARTIALLY_COMPLETED,
                JobStatus.FAILED,
            ):
                logger.info(
                    "Job %s already in terminal status %s; skipping",
                    job_id,
                    job.status.value,
                )
                return

            # 2. Transition status to PROCESSING
            job.status = JobStatus.PROCESSING
            await session.commit()
            logger.info("Started background processing for Job %s", job_id)

            loop = asyncio.get_running_loop()

            # 3. Process each recipient with strict fault isolation
            for recipient in job.recipients:
                if recipient.status != RecipientStatus.PENDING:
                    continue

                try:
                    # Defensive check: simulate/handle faulty recipient scenario for testing
                    if recipient.recipient_name.lower().startswith("__fail__"):
                        raise ValueError("Simulated recipient failure for testing")

                    # Generate unique human-readable certificate ID
                    cert_code = uuid.uuid4().hex[:8].upper()
                    cert_id = f"CERT-{job.issue_date.year}-{cert_code}"
                    dest_path = str(
                        storage_service.get_certificate_path(job.id, cert_id)
                    )
                    verify_url = f"/api/v1/certificates/{cert_id}/verify"

                    # Offload CPU-bound PDF rendering to thread pool
                    await loop.run_in_executor(
                        thread_pool,
                        self._render_certificate_sync,
                        recipient.recipient_name,
                        job.event_name,
                        job.issuer_name,
                        job.certificate_title,
                        job.issue_date,
                        cert_id,
                        dest_path,
                        verify_url,
                    )

                    # Update recipient record on success
                    recipient.status = RecipientStatus.SUCCESS
                    recipient.certificate_id = cert_id
                    recipient.certificate_file_path = dest_path
                    recipient.generated_at = datetime.now(UTC)
                    recipient.error_message = None

                except Exception as exc:  # noqa: BLE001
                    # FAULT ISOLATION: Trap any error for this recipient and proceed
                    logger.error(
                        "Failed to generate certificate for recipient %s (ID: %s): %s",
                        recipient.recipient_name,
                        recipient.id,
                        exc,
                    )
                    recipient.status = RecipientStatus.FAILED
                    recipient.error_message = str(exc)
                    recipient.certificate_id = None
                    recipient.certificate_file_path = None

                finally:
                    # Accurately compute counts from current recipient states
                    job.success_count = sum(
                        1 for r in job.recipients if r.status == RecipientStatus.SUCCESS
                    )
                    job.failed_count = sum(
                        1 for r in job.recipients if r.status == RecipientStatus.FAILED
                    )
                    job.processed_count = job.success_count + job.failed_count
                    await session.commit()

            # 4. Finalize Job Status
            if job.failed_count == 0:
                job.status = JobStatus.COMPLETED
            elif job.success_count > 0:
                job.status = JobStatus.PARTIALLY_COMPLETED
            else:
                job.status = JobStatus.FAILED

            job.completed_at = datetime.now(UTC)
            await session.commit()
            logger.info(
                "Job %s finished with status %s (Total: %d, Success: %d, Failed: %d)",
                job.id,
                job.status.value,
                job.total_recipients,
                job.success_count,
                job.failed_count,
            )

        except Exception as e:  # noqa: BLE001
            logger.critical(
                "Unexpected error in Job %s execution: %s", job_id, e, exc_info=True
            )
            try:
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(UTC)
                await session.commit()
            except Exception as rollback_err:  # noqa: BLE001
                logger.error("Failed to commit final failed state: %s", rollback_err)


job_service = JobService()
