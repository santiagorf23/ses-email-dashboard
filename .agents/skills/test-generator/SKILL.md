---
name: test-generator
description: Genera tests unitarios y de integración para el código existente, siguiendo patrones del proyecto
model: sonnet
allowed-tools: [Read, Grep, Glob, Write, Bash]
---

# Test Generator Skill

## Goal

Generar una suite de tests automatizados para el código existente, cubriendo casos normales, edge cases y errores, siguiendo las convenciones del proyecto.

## When to use

- Cuando un módulo crítico no tiene tests
- Después de implementar nueva funcionalidad
- Antes de refactorizar código existente
- Como parte de un plan de Deep Work

## Steps

### 1. Análisis del Código a Testear

```bash
# Identificar módulos sin tests
find backend/ -name "*.py" ! -name "__init__.py" ! -path "*/venv/*" | sort

# Verificar si existe directorio de tests
ls -la backend/tests/ 2>/dev/null || echo "No tests directory"

# Identificar funciones públicas
rg -n "^def |^async def " backend/routers/ backend/db/ backend/models/
```

### 2. Configurar Entorno de Tests

```bash
# Agregar dependencias de testing
cat >> backend/requirements.txt << 'EOF'
pytest
pytest-asyncio
pytest-cov
httpx
EOF

# Crear estructura de tests
mkdir -p backend/tests
touch backend/tests/__init__.py
```

### 3. Generar Tests Unitarios

Para cada módulo, crear archivo de tests:

**Patrón para routers:**
```python
# backend/tests/test_auth.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.fixture
def client():
    return AsyncClient(app=app, base_url="http://test")

@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_login_success(client):
    response = await client.post("/api/auth/login", data={
        "username": "admin",
        "password": "admin123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

**Patrón para database:**
```python
# backend/tests/test_database.py
import pytest
from db.database import get_pool, close_pool

@pytest.mark.asyncio
async def test_pool_creation():
    pool = await get_pool()
    assert pool is not None
    await close_pool()
```

### 4. Generar Tests de Integración

```python
# backend/tests/test_emails_integration.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.fixture
async def auth_token():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/auth/login", data={
            "username": "admin",
            "password": "admin123"
        })
        return response.json()["access_token"]

@pytest.mark.asyncio
async def test_list_emails(auth_token):
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/emails/",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```

### 5. Configurar pytest

```ini
# backend/pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
```

### 6. Ejecutar y Generar Coverage

```bash
cd backend
pytest --cov=. --cov-report=html --cov-report=term
```

## Validation

- [ ] Tests creados para cada router
- [ ] Tests creados para database layer
- [ ] pytest ejecuta sin errores
- [ ] Coverage mínimo 60%
- [ ] Tests pasan en clean environment

## Output

```markdown
# Test Coverage Report

## Resumen
- Tests totales: X
- Pasan: X
- Fallan: X
- Coverage: X%

## Por Módulo
| Módulo | Tests | Coverage |
|--------|-------|----------|
| routers/auth.py | X | X% |
| routers/emails.py | X | X% |
| db/database.py | X | X% |
```

## Notes

- Usar `pytest-asyncio` para tests async (FastAPI es async)
- `httpx` es el cliente HTTP recomendado para testear FastAPI
- No mockear la DB en tests de integración, usar testcontainers o DB real de test
- Para este proyecto, empezar con tests de los endpoints críticos (auth, emails)
