import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_job_lifecycle_and_progress_tracking(client: AsyncClient):
    """Test creating a job, verifying initial 202 response, and polling its progress until COMPLETED."""
    payload = {
        "event_name": "Distributed Systems Intensive",
        "issuer_name": "Cloud Native Academy",
        "certificate_title": "Certificate of Completion",
        "recipients": [
            {"name": "Dev One", "email": "dev1@example.com"},
            {"name": "Dev Two", "email": "dev2@example.com"},
            {"name": "Dev Three", "email": "dev3@example.com"},
        ],
    }

    # 1. Create Job - returns 202 Accepted with PENDING status
    create_resp = await client.post("/api/v1/jobs", json=payload)
    assert create_resp.status_code == 202
    initial_data = create_resp.json()
    assert initial_data["status"] == "PENDING"
    assert initial_data["total_recipients"] == 3
    job_id = initial_data["job_id"]

    # 2. Poll job status after background processing
    done_resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert done_resp.status_code == 200
    data = done_resp.json()

    assert data["status"] == "COMPLETED"
    assert data["total_recipients"] == 3
    assert data["processed_count"] == 3
    assert data["success_count"] == 3
    assert data["failed_count"] == 0
    assert data["progress_percentage"] == 100.0
    assert data["completed_at"] is not None
    assert data["zip_download_url"] == f"/api/v1/jobs/{job_id}/download"

    # Verify recipient details
    assert len(data["recipients"]) == 3
    for rec in data["recipients"]:
        assert rec["status"] == "SUCCESS"
        assert rec["certificate_id"] is not None
        assert (
            rec["download_url"]
            == f"/api/v1/certificates/{rec['certificate_id']}/download"
        )
        assert rec["error_message"] is None


@pytest.mark.asyncio
async def test_job_recipients_pagination(client: AsyncClient):
    """Test pagination query parameters on job status endpoint."""
    payload = {
        "event_name": "Pagination Seminar",
        "issuer_name": "Data Org",
        "recipients": [
            {"name": "User 1", "email": "u1@example.com"},
            {"name": "User 2", "email": "u2@example.com"},
            {"name": "User 3", "email": "u3@example.com"},
        ],
    }

    create_resp = await client.post("/api/v1/jobs", json=payload)
    assert create_resp.status_code == 202
    job_id = create_resp.json()["job_id"]

    # Paginate with limit=2, offset=0
    page1_resp = await client.get(f"/api/v1/jobs/{job_id}?limit=2&offset=0")
    assert page1_resp.status_code == 200
    assert len(page1_resp.json()["recipients"]) == 2

    # Paginate with limit=2, offset=2
    page2_resp = await client.get(f"/api/v1/jobs/{job_id}?limit=2&offset=2")
    assert page2_resp.status_code == 200
    assert len(page2_resp.json()["recipients"]) == 1
