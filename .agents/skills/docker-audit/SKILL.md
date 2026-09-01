---
name: docker-audit
description: Audita Dockerfiles, docker-compose.yml y configuración de contenedores contra best practices de seguridad y rendimiento
model: sonnet
allowed-tools: [Read, Grep, Glob, Bash, Edit]
---

# Docker Audit Skill

## Goal

Revisar toda la configuración de Docker del proyecto para detectar problemas de seguridad, rendimiento y mantenibilidad, y aplicar las mejores prácticas de la industria.

## When to use

- Antes de cada deploy a producción
- Cuando se crean o modifican Dockerfiles
- Durante auditorías de seguridad periódicas
- Al configurar servicios Docker por primera vez

## Steps

### 1. Auditoría de Dockerfiles

```bash
# Buscar todos los Dockerfiles
find . -name "Dockerfile*" -type f

# Verificar problemas comunes en cada uno
for f in $(find . -name "Dockerfile" -type f); do
    echo "=== Auditing: $f ==="
    
    # ¿Usa imagen base específica (no :latest)?
    rg -n "^FROM" $f
    
    # ¿Tiene USER directive?
    rg -n "^USER" $f || echo "WARN: No USER directive"
    
    # ¿Usa multi-stage build?
    rg -n "^FROM.*as" $f || echo "INFO: No multi-stage build"
    
    # ¿Copia .env o secrets?
    rg -n "COPY.*\.env" $f && echo "CRITICAL: Copies .env"
    
    # ¿Instala dependencias de desarrollo?
    rg -n "pip install.*pytest|pip install.*mypy" $f && echo "WARN: Dev deps in prod"
done
```

### 2. Auditoría de docker-compose.yml

```bash
# Verificar secrets hardcodeados
rg -n "(password|secret|key|token)\s*:" docker-compose.yml

# Verificar health checks
rg -n "healthcheck:" docker-compose.yml || echo "WARN: No healthchecks"

# Verificar restart policies
rg -n "restart:" docker-compose.yml || echo "WARN: No restart policy"

# Verificar resource limits
rg -n "mem_limit|cpus:" docker-compose.yml || echo "WARN: No resource limits"

# Verificar puertos expuestos innecesariamente
rg -n "ports:" docker-compose.yml
```

### 3. Verificar .dockerignore

```bash
if [ ! -f .dockerignore ]; then
    echo "CRITICAL: No .dockerignore file"
    echo "Creating .dockerignore..."
fi
```

### 4. Generar .dockerignore (si no existe)

```
# .dockerignore
.git
.gitignore
.env
.env.*
*.md
!README.md
__pycache__
*.pyc
*.pyo
venv/
.venv/
.pytest_cache
htmlcov/
.coverage
*.log
.vscode/
.idea/
node_modules/
frontend/
database/
scripts/
Makefile
docker-compose.yml
Dockerfile
.dwp/
.agents/
```

### 5. Corregir Dockerfile del Backend

```dockerfile
# backend/Dockerfile - Versión mejorada
FROM python:3.11-slim AS builder

WORKDIR /app

# Instalar dependencias en etapa separada
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Etapa de producción
FROM python:3.11-slim

# Crear usuario no-root
RUN adduser --disabled-password --no-create-home appuser

WORKDIR /app

# Copiar dependencias del builder
COPY --from=builder /root/.local /home/appuser/.local

# Copiar código
COPY . .

# Cambiar a usuario no-root
USER appuser

# Configurar PATH para el usuario
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6. Corregir docker-compose.yml

Cambiar secrets hardcodeados por variables de entorno:

```yaml
services:
  db:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-user}"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-user}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-ses_dashboard}
      SECRET_KEY: ${SECRET_KEY}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"]
      interval: 10s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  frontend:
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
```

## Validation

- [ ] Todos los Dockerfiles auditados
- [ ] docker-compose.yml revisado
- [ ] .dockerignore creado/actualizado
- [ ] Secrets no hardcodeados
- [ ] Health checks configurados
- [ ] Usuario no-root en Dockerfiles

## Output

```markdown
# Docker Audit Report

## Resumen
- Dockerfiles auditados: X
- Issues encontrados: X
- Críticos: X

## Hallazgos

### [CRITICAL] Dockerfile ejecuta como root
- **Archivo:** backend/Dockerfile
- **Fix:** Agregar USER appuser

### [HIGH] Secrets hardcodeados en docker-compose.yml
- **Archivo:** docker-compose.yml:línea
- **Fix:** Usar ${VARIABLE} syntax

## Cambios Aplicados
1. .dockerignore creado
2. Dockerfile actualizado con multi-stage build
3. docker-compose.yml actualizado con health checks
```

## Notes

- `hadolint` es la herramienta estándar para linting de Dockerfiles: `docker run --rm -i hadolint/hadolint < Dockerfile`
- Multi-stage builds reducen el tamaño de imagen significativamente
- Siempre usar imágenes con tags específicos, nunca `:latest`
- `restart: unless-stopped` es la política recomendada para servicios
