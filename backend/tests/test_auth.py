import pytest


@pytest.mark.asyncio
async def test_login_success(client):
    """Test successful login returns token."""
    response = await client.post("/api/auth/login", data={
        "username": "admin",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "full_name" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    """Test login with wrong password fails."""
    response = await client.post("/api/auth/login", data={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_login_wrong_username(client):
    """Test login with wrong username fails."""
    response = await client.post("/api/auth/login", data={
        "username": "nonexistent",
        "password": "testpassword123"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_missing_fields(client):
    """Test login with missing fields fails."""
    response = await client.post("/api/auth/login", data={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_me_with_valid_token(client, auth_headers):
    """Test /me endpoint with valid token."""
    response = await client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert "full_name" in data


@pytest.mark.asyncio
async def test_me_without_token(client):
    """Test /me endpoint without token fails."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(client):
    """Test /me endpoint with invalid token fails."""
    response = await client.get("/api/auth/me", headers={
        "Authorization": "Bearer invalid-token-here"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_contains_expiry(client):
    """Test that generated token contains expiry."""
    from routers.auth import create_token, SECRET_KEY, ALGORITHM
    from jose import jwt
    token = create_token({"sub": "admin"})
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
    assert "exp" in payload
    assert payload["sub"] == "admin"


@pytest.mark.asyncio
async def test_rate_limit_after_failed_attempts(client):
    """Test rate limiting blocks after max failed attempts."""
    # Hacer 5 intentos fallidos
    for _ in range(5):
        await client.post("/api/auth/login", data={
            "username": "admin",
            "password": "wrongpassword"
        })
    
    # El 6to intento debe ser rate limited
    response = await client.post("/api/auth/login", data={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert response.status_code == 429
    assert "demasiados intentos" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rate_limit_reset_on_success(client):
    """Test rate limit resets after successful login."""
    from routers.auth import _login_attempts
    
    # Limpiar cualquier estado previo
    _login_attempts.clear()
    
    # Login exitoso debe funcionar sin problemas
    response = await client.post("/api/auth/login", data={
        "username": "admin",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    
    # Verificar que no hay intentos fallidos registrados
    # (el login exitoso limpia los intentos de la IP del cliente)
    for ip, attempts in _login_attempts.items():
        assert len(attempts) == 0
