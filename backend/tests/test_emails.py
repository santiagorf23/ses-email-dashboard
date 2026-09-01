import pytest


@pytest.mark.asyncio
async def test_list_emails_requires_auth(client):
    """Test listing emails requires authentication."""
    response = await client.get("/api/emails", follow_redirects=False)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_emails_returns_paginated(client, auth_headers):
    """Test listing emails returns paginated response."""
    response = await client.get("/api/emails", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "per_page" in data
    assert "pages" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_list_emails_pagination_params(client, auth_headers):
    """Test pagination parameters work."""
    response = await client.get(
        "/api/emails?page=1&per_page=10",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["per_page"] == 10


@pytest.mark.asyncio
async def test_list_emails_invalid_page(client, auth_headers):
    """Test invalid page parameter fails."""
    response = await client.get(
        "/api/emails?page=0",
        headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_emails_per_page_max(client, auth_headers):
    """Test per_page cannot exceed 100."""
    response = await client.get(
        "/api/emails?per_page=101",
        headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_emails_requires_auth(client):
    """Test search requires authentication."""
    response = await client.get("/api/emails/search?q=test", follow_redirects=False)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_search_emails_returns_results(client, auth_headers):
    """Test search returns results."""
    response = await client.get(
        "/api/emails/search?q=test",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_search_emails_empty_query(client, auth_headers):
    """Test search with empty query fails."""
    response = await client.get(
        "/api/emails/search?q=",
        headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_stats_requires_auth(client):
    """Test stats endpoint requires authentication."""
    response = await client.get("/api/emails/stats", follow_redirects=False)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stats_returns_response(client, auth_headers):
    """Test stats endpoint returns data."""
    response = await client.get("/api/emails/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_sent" in data
    assert "total_delivered" in data
    assert "total_bounce" in data
    assert "total_complaint" in data
    assert "delivery_rate" in data
    assert "bounce_rate" in data


@pytest.mark.asyncio
async def test_blocked_requires_auth(client):
    """Test blocked endpoint requires authentication."""
    response = await client.get("/api/emails/blocked", follow_redirects=False)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_blocked_returns_list(client, auth_headers):
    """Test blocked endpoint returns list."""
    response = await client.get("/api/emails/blocked", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_email_requires_auth(client):
    """Test get single email requires authentication."""
    response = await client.get("/api/emails/1", follow_redirects=False)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_email_not_found(client, auth_headers):
    """Test get non-existent email returns 404."""
    response = await client.get(
        "/api/emails/999999",
        headers=auth_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_emails_filter_status(client, auth_headers):
    """Test filtering by status parameter."""
    response = await client.get(
        "/api/emails?status=delivered",
        headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_emails_filter_invalid_status(client, auth_headers):
    """Test filtering by invalid status returns 400."""
    response = await client.get(
        "/api/emails?status=invalid_status",
        headers=auth_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_emails_filter_by_date(client, auth_headers):
    """Test filtering by date range."""
    response = await client.get(
        "/api/emails?date_from=2024-01-01&date_to=2024-12-31",
        headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_emails_filter_by_email_to(client, auth_headers):
    """Test filtering by recipient email."""
    response = await client.get(
        "/api/emails?email_to=test",
        headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_emails_filter_by_subject(client, auth_headers):
    """Test filtering by subject."""
    response = await client.get(
        "/api/emails?subject=test",
        headers=auth_headers
    )
    assert response.status_code == 200
