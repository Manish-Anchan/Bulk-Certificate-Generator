import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_fault_isolation_individual_failure(client: AsyncClient):
    """Test that a failure in one certificate does NOT block other valid certificates,

    and that the job concludes with PARTIALLY_COMPLETED status and detailed error information.
    """
    payload = {
        "event_name": "Resilient Microservices Summit",
        "issuer_name": "Reliability Institute",
        "recipients": [
            {"name": "Valid Recipient One", "email": "valid1@example.com"},
            {"name": "__fail__ Faulty Recipient", "email": "faulty@example.com"},
            {"name": "Valid Recipient Two", "email": "valid2@example.com"},
        ],
    }

    # 1. Enqueue job (background processing executes automatically)
    resp = await client.post("/api/v1/jobs", json=payload)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # 2. Retrieve final status
    status_resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()

    # 3. Verify Job-level fault isolation metrics
    assert data["status"] == "PARTIALLY_COMPLETED"
    assert data["total_recipients"] == 3
    assert data["processed_count"] == 3
    assert data["success_count"] == 2
    assert data["failed_count"] == 1
    assert data["progress_percentage"] == 100.0

    # 4. Verify Item-level outcomes
    recipients = data["recipients"]
    assert len(recipients) == 3

    # Recipient 1: Succeeded
    r1 = recipients[0]
    assert r1["recipient_name"] == "Valid Recipient One"
    assert r1["status"] == "SUCCESS"
    assert r1["certificate_id"] is not None
    assert r1["download_url"] is not None
    assert r1["error_message"] is None

    # Recipient 2: Failed gracefully with error reason captured
    r2 = recipients[1]
    assert r2["recipient_name"] == "__fail__ Faulty Recipient"
    assert r2["status"] == "FAILED"
    assert r2["certificate_id"] is None
    assert r2["download_url"] is None
    assert "Simulated recipient failure for testing" in r2["error_message"]

    # Recipient 3: Succeeded despite previous failure!
    r3 = recipients[2]
    assert r3["recipient_name"] == "Valid Recipient Two"
    assert r3["status"] == "SUCCESS"
    assert r3["certificate_id"] is not None
    assert r3["download_url"] is not None
    assert r3["error_message"] is None


@pytest.mark.asyncio
async def test_all_recipients_failed_job_status(client: AsyncClient):
    """Test that if all recipients fail, the job status is FAILED."""
    payload = {
        "event_name": "Failure Test Workshop",
        "issuer_name": "Test Org",
        "recipients": [
            {"name": "__fail__ Recipient 1", "email": "f1@example.com"},
            {"name": "__fail__ Recipient 2", "email": "f2@example.com"},
        ],
    }

    resp = await client.post("/api/v1/jobs", json=payload)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    status_resp = await client.get(f"/api/v1/jobs/{job_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()

    assert data["status"] == "FAILED"
    assert data["success_count"] == 0
    assert data["failed_count"] == 2
    assert data["zip_download_url"] is None
