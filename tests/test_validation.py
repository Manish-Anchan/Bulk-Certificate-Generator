import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_empty_recipients_fails_validation(client: AsyncClient):
    """Test that submitting an empty recipient list fails with 422 Unprocessable Entity."""
    payload = {
        "event_name": "AI Workshop",
        "issuer_name": "AI Labs",
        "recipients": [],
    }

    response = await client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("recipients" in str(err["loc"]) for err in errors)


@pytest.mark.asyncio
async def test_missing_event_name_fails(client: AsyncClient):
    """Test that missing required event_name fails with 422."""
    payload = {
        "issuer_name": "AI Labs",
        "recipients": [{"name": "Dan", "email": "dan@example.com"}],
    }

    response = await client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_empty_string_event_name_fails(client: AsyncClient):
    """Test that whitespace-only event_name fails validation."""
    payload = {
        "event_name": "   ",
        "issuer_name": "AI Labs",
        "recipients": [{"name": "Dan", "email": "dan@example.com"}],
    }

    response = await client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_recipient_email_format_fails(client: AsyncClient):
    """Test that an invalid recipient email fails with 422."""
    payload = {
        "event_name": "Webinar",
        "issuer_name": "Speaker",
        "recipients": [
            {"name": "Valid User", "email": "valid@example.com"},
            {"name": "Invalid User", "email": "not-an-email-address"},
        ],
    }

    response = await client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("email" in str(err["loc"]) for err in errors)


@pytest.mark.asyncio
async def test_whitespace_only_recipient_name_fails(client: AsyncClient):
    """Test that empty or whitespace recipient name fails with 422."""
    payload = {
        "event_name": "Webinar",
        "issuer_name": "Speaker",
        "recipients": [{"name": "   ", "email": "valid@example.com"}],
    }

    response = await client.post("/api/v1/jobs", json=payload)
    assert response.status_code == 422
