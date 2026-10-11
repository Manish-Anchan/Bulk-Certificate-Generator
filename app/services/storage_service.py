import zipfile
from pathlib import Path

from app.core.config import settings
from app.core.logging import logger


class StorageService:
    """Manages file persistence for generated PDF certificates and batch ZIP archives."""

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir) if base_dir else settings.storage_path
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_job_dir(self, job_id: str) -> Path:
        """Get or create the storage directory for a specific job."""
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def get_certificate_path(self, job_id: str, certificate_id: str) -> Path:
        """Resolve the path for a specific certificate PDF."""
        return self.get_job_dir(job_id) / f"{certificate_id}.pdf"

    def save_certificate(self, job_id: str, certificate_id: str, pdf_bytes: bytes) -> str:
        """Save a certificate PDF to disk and return its relative/absolute path."""
        target_path = self.get_certificate_path(job_id, certificate_id)
        target_path.write_bytes(pdf_bytes)
        logger.debug("Saved certificate %s to %s", certificate_id, target_path)
        return str(target_path)

    def certificate_exists(self, file_path: str | Path | None) -> bool:
        """Check if a certificate file exists on disk."""
        if not file_path:
            return False
        return Path(file_path).is_file()

    def get_job_zip_path(self, job_id: str) -> Path:
        """Resolve the path for the bulk ZIP archive of a job."""
        return self.get_job_dir(job_id) / f"certificates_{job_id}.zip"

    def create_job_zip(self, job_id: str, certificates: list[tuple[str, str]]) -> Path:
        """Create or update a zip archive of all generated certificates for a job.

        Args:
            job_id: ID of the parent job.
            certificates: List of tuples (file_display_name, absolute_or_relative_path).

        Returns:
            Path to the created zip file.
        """
        zip_path = self.get_job_zip_path(job_id)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for display_name, file_path in certificates:
                path_obj = Path(file_path)
                if path_obj.is_file():
                    zipf.write(path_obj, arcname=display_name)
                else:
                    logger.warning("File %s not found when building zip for job %s", file_path, job_id)

        logger.info("Created batch zip for job %s with %d files", job_id, len(certificates))
        return zip_path


storage_service = StorageService()
