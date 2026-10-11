import uuid
from datetime import UTC, date, datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.recipient import Recipient


class JobStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
    FAILED = "FAILED"


class Job(Base):
    """Database model representing a bulk certificate generation job."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    event_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    issuer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    certificate_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Certificate of Completion",
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)

    status: Mapped[JobStatus] = mapped_column(
        SQLEnum(JobStatus),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )

    total_recipients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships (with lazy='selectin' for clean async loading)
    recipients: Mapped[list["Recipient"]] = relationship(
        "Recipient",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Recipient.created_at",
    )

    @property
    def progress_percentage(self) -> float:
        """Calculate the job completion percentage."""
        if self.total_recipients == 0:
            return 100.0 if self.status in [JobStatus.COMPLETED, JobStatus.PARTIALLY_COMPLETED] else 0.0
        return round((self.processed_count / self.total_recipients) * 100.0, 2)
