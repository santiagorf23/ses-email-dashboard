# SES Mail Dashboard - Skills & Agents Catalog

> Catálogo de todos los skills y agents disponibles en el proyecto.
> Última actualización: 2026-09-01

---

## Skills

| Skill | Modelo | Tier | Descripción | Archivo |
|-------|--------|------|-------------|---------|
| `security-review` | sonnet | standard | Auditoría de seguridad: SQL injection, XSS, secrets, dependencias CVE | `.agents/skills/security-review/SKILL.md` |
| `code-quality` | sonnet | standard | Linting, análisis de tipo, formato, code smells | `.agents/skills/code-quality/SKILL.md` |
| `test-generator` | sonnet | standard | Generación de tests unitarios y de integración | `.agents/skills/test-generator/SKILL.md` |
| `docker-audit` | sonnet | standard | Auditoría de Dockerfiles, docker-compose, .dockerignore | `.agents/skills/docker-audit/SKILL.md` |
| `docs-sync` | sonnet | standard | Sincronización de documentación con código real | `.agents/skills/docs-sync/SKILL.md` |
| `api-review` | sonnet | standard | Revisión de diseño REST, rutas, paginación, errores | `.agents/skills/api-review/SKILL.md` |

---

## Agents

| Agent | Modelo | Descripción | Archivo |
|-------|--------|-------------|---------|
| `quality-guardian` | sonnet | Guardián global de calidad - aplica estándares a TODO el código | `.agents/agents/quality-guardian.md` |
| `security-agent` | sonnet | Especialista en encontrar y corregir vulnerabilidades | `.agents/agents/security-agent.md` |
| `code-reviewer` | sonnet | Revisión de código: calidad, estilo, patrones, buenas prácticas | `.agents/agents/code-reviewer.md` |
| `infra-reviewer` | sonnet | Auditoría de Docker, despliegue, variables de entorno, setup | `.agents/agents/infra-reviewer.md` |

---

## Cómo Usar

### Para cada tarea de código:

```
1. Implementar el cambio
2. Invocar quality-guardian para verificar
3. Si PASS → commit
4. Si FAIL → corregir y repetir
```

### Para auditorías completas:

```
1. security-review → Hallazgos de seguridad
2. code-quality → Calidad de código
3. docker-audit → Infraestructura
4. docs-sync → Documentación
5. api-review → Diseño de API
```

### Para code review manual:

```
1. code-reviewer → Revisión de calidad
2. security-agent → Revisión de seguridad
3. infra-reviewer → Revisión de infraestructura
```

---

## Integación con Deep Work Plan

Cada tarea en un DWP debe:

1. **Al inicio**: Leer este catálogo para identificar skills relevantes
2. **Durante**: Usar skills según la naturaleza de la tarea
3. **Al final**: Ejecutar `quality-guardian` como gate de calidad
4. **En commit**: Incluir resultado del quality gate en el mensaje

### Template para task files:

```markdown
## Skills & Agents Used

| Skill/Agent | Propósito |
|-------------|-----------|
| `security-review` | Verificar no vulnerabilidades introducidas |
| `quality-guardian` | Gate de calidad final |
```

---

## Dependencias Requeridas

### Python (agregar a requirements.txt)

```txt
# Testing
pytest
pytest-asyncio
pytest-cov
httpx

# Code Quality
ruff
mypy
bandit

# Security
pip-audit
```

### Herramientas del Sistema

```bash
# Docker linting
docker run --rm -i hadolint/hadolint < Dockerfile

# Security scanning
pip install pip-audit
pip-audit -r requirements.txt
```

---

## Estándares del Proyecto

### Security (INQUEBRANTABLE)

- NO secrets hardcodeados
- NO SQL con f-strings
- NO eval()/exec()
- SI queries parametrizadas
- SI bcrypt/argon2 para passwords
- SI tokens JWT con expiración

### Quality (RECOMENDADO)

- Type hints en funciones públicas
- Logging (no print)
- Funciones < 50 líneas
- Archivos < 300 líneas
- Sin bare except
- Sin código muerto

### Architecture (RECOMENDADO)

- Separación de responsabilidades
- Consistencia con patrones existentes
- Database layer separado de routes
- Config en variables de entorno

### Infrastructure (OBLIGATORIO para Docker)

- .dockerignore completo
- USER directive en Dockerfiles
- Health checks en servicios
- Restart policies configuradas
- No secrets en docker-compose.yml
