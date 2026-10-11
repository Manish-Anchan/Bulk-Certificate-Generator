import io
import zipfile

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_retrieve_individual_and_bulk_certificates(client: AsyncClient):
    """Test retrieving individual PDF certificate and bulk ZIP archive."""
    payload = {
        "event_name": "API Design & Security 2026",
        "issuer_name": "Global Tech Certifications",
        "certificate_title": "Certificate of Completion",
        "recipients": [
            {"name": "Grace Hopper", "email": "grace@navy.mil"},
            {"name": "Ada Lovelace", "email": "ada@computing.org"},
        ],
    }

    # 1. Create and process job (background tasks execute automatically)
    resp = await client.post("/api/v1/jobs", json=payload)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    # 2. Get status to find certificate IDs
    status_resp = await client.get(f"/api/v1/jobs/{job_id}")

    data = status_resp.json()
    assert data["status"] == "COMPLETED"
    cert_id_grace = data["recipients"][0]["certificate_id"]
    cert_id_ada = data["recipients"][1]["certificate_id"]

    # 3. Download individual PDF
    download_resp = await client.get(f"/api/v1/certificates/{cert_id_grace}/download")
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/pdf"
    assert download_resp.content.startswith(b"%PDF-")
    assert len(download_resp.content) > 1000

    # 4. Verify certificate metadata endpoint
    meta_resp = await client.get(f"/api/v1/certificates/{cert_id_grace}")
    assert meta_resp.status_code == 200
    assert meta_resp.json()["recipient_name"] == "Grace Hopper"
    assert meta_resp.json()["certificate_id"] == cert_id_grace

    # 5. Public verification endpoint
    verify_resp = await client.get(f"/api/v1/certificates/{cert_id_grace}/verify")
    assert verify_resp.status_code == 200
    verify_data = verify_resp.json()
    assert verify_data["valid"] is True
    assert verify_data["recipient_name"] == "Grace Hopper"
    assert verify_data["event_name"] == "API Design & Security 2026"
    assert verify_data["issuer_name"] == "Global Tech Certifications"

    # 6. Bulk download as ZIP
    zip_resp = await client.get(f"/api/v1/jobs/{job_id}/download")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"

    # Read and inspect ZIP in-memory
    zip_buffer = io.BytesIO(zip_resp.content)
    with zipfile.ZipFile(zip_buffer) as zf:
        namelist = zf.namelist()
        assert len(namelist) == 2
        assert any(cert_id_grace in fname for fname in namelist)
        assert any(cert_id_ada in fname for fname in namelist)


@pytest.mark.asyncio
async def test_retrieval_404_for_unknown_certificate(client: AsyncClient):
    """Test that requesting a non-existent certificate returns 404."""
    resp = await client.get("/api/v1/certificates/NON-EXISTENT-ID/download")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verification_404_for_unknown_certificate(client: AsyncClient):
    """Test that verifying a non-existent certificate returns 404."""
    resp = await client.get("/api/v1/certificates/NON-EXISTENT-ID/verify")
    assert resp.status_code == 404
    assert "could not be verified" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_zip_download_404_for_unknown_job(client: AsyncClient):
    """Test that downloading zip for unknown job returns 404."""
    resp = await client.get("/api/v1/jobs/unknown-job-id/download")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_endpoint_serves_html(client: AsyncClient):
    """Test that GET / returns the interactive web dashboard HTML."""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Bulk Certificate Generator" in resp.text
