import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_generation_job_success(client: AsyncClient):
    """Test creating a bulk certificate generation job returns 202 Accepted and correct structure."""
    payload = {
        "event_name": "Full Stack Cloud Architecture",
        "issuer_name": "Tech Academy Worldwide",
        "certificate_title": "Certificate of Completion",
        "issue_date": "2026-10-10",
        "recipients": [
            {
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "custom_fields": {"grade": "Distinction"},
            },
            {
                "name": "Bob Smith",
                "email": "bob@example.com",
            },
        ],
    }

    response = await client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202

    data = response.json()
    assert "job_id" in data
    assert data["status"] == "PENDING"
    assert data["total_recipients"] == 2
    assert data["status_url"] == f"/api/v1/jobs/{data['job_id']}"
    assert "accepted and enqueued" in data["message"].lower()


@pytest.mark.asyncio
async def test_create_job_defaults_applied(client: AsyncClient):
    """Test that default certificate title is applied if omitted."""
    payload = {
        "event_name": "Python Microservices",
        "issuer_name": "Dev Institute",
        "recipients": [{"name": "Carol White", "email": "carol@example.com"}],
    }

    response = await client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["total_recipients"] == 1
