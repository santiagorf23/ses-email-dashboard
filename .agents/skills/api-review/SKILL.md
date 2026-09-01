---
name: api-review
description: Revisa el diseño de la API REST contra convenciones, detecta rutas conflictivas, problemas de paginación y manejo de errores
model: sonnet
allowed-tools: [Read, Grep, Glob, Bash]
---

# API Review Skill

## Goal

Auditar el diseño de la API REST del proyecto contra convenciones de la industria, detectando problemas de rutas, paginación, formato de respuesta, manejo de errores y seguridad.

## When to use

- Cuando se diseñan nuevos endpoints
- Durante code review de cambios en la API
- Antes de documentar la API para clientes externos
- Como parte de una auditoría de calidad general

## Steps

### 1. Mapear Todos los Endpoints

```bash
# Extraer todos los endpoints definidos
rg -n "@app\.\(get\|post\|put\|delete\|patch\)" backend/routers/ --type py

# Extraer prefijos de router
rg -n "prefix=" backend/main.py
```

### 2. Verificar Convenciones REST

Para cada endpoint, verificar:

| Convención | Esperado | Ejemplo |
|------------|----------|---------|
| Recursos en plural | `/emails` no `/email` | GET /api/emails |
| HTTP methods correctos | GET para lectura, POST para crear | |
| Códigos de respuesta | 200 OK, 201 Created, 404 Not Found | |
| Nesting para sub-recursos | `/emails/{id}/events` | |

### 3. Detectar Rutas Conflictivas

```bash
# Buscar rutas que podrían colisionar
rg -n "email_id|search|{id}" backend/routers/emails.py

# Verificar orden de rutas (FastAPI procesa en orden)
rg -n "@router\.\(get\|post\)" backend/routers/emails.py
```

**Problema conocido:**
- `GET /api/emails/{email_id}` (line 226)
- `GET /api/emails/search` (line 174)
- Si `email_id` no tiene type hint `int`, `"search"` podría matchear como `email_id`

### 4. Verificar Paginación

```bash
# Buscar endpoints que devuelven listas
rg -n "SELECT.*FROM.*email_send" backend/routers/emails.py

# Buscar LIMIT/OFFSET
rg -n "LIMIT|OFFSET" backend/routers/emails.py
```

**Problema conocido:**
- `GET /api/emails/blocked` tiene `LIMIT 200` hardcodeado
- No hay paginación con page/size parameters

### 5. Verificar Formato de Respuesta

```bash
# Buscar patrones de respuesta inconsistentes
rg -n "return {" backend/routers/ --type py
rg -n "return \[" backend/routers/ --type py
```

**Verificar:**
- ¿Todos los endpoints exitosos devuelven 200?
- ¿Los errores devuelven el código correcto (400, 401, 404, 500)?
- ¿El formato de error es consistente?

### 6. Verificar Health Check

```bash
# Verificar health check
rg -n "health" backend/main.py
```

**Problema conocido:**
- Health check no verifica conectividad con DB
- Debería hacer `SELECT 1` para confirmar DB accesible

### 7. Verificar Rate Limiting

```bash
# Buscar rate limiting
rg -n "rate.limit|throttl|limiter" backend/ --type py
```

**Problema conocido:**
- No hay rate limiting en `/api/auth/login`
- Vulnerable a brute force

### 8. Verificar Versionado

```bash
# Verificar si hay versionado de API
rg -n "/v1/|/v2/|version" backend/
```

## Validation

- [ ] Todos los endpoints documentados
- [ ] Sin rutas conflictivas
- [ ] Paginación implementada en endpoints de lista
- [ ] Health check verifica DB
- [ ] Rate limiting en auth
- [ ] Formato de respuesta consistente

## Output

```markdown
# API Review Report

## Endpoints Encontrados
| Método | Ruta | Archivo:Línea | Estado |
|--------|------|---------------|--------|
| GET | /api/health | main.py:20 | OK |
| POST | /api/auth/login | auth.py:61 | WARN |
| GET | /api/emails/ | emails.py:60 | OK |

## Problemas de Diseño

### [HIGH] Ruta conflictiva /search vs /{email_id}
- **Archivos:** emails.py:líneas
- **Problema:** /search podría colisionar con /{email_id}
- **Fix:** Mover /search antes de /{email_id} o usar query param

### [MEDIUM] Sin paginación en blocked emails
- **Archivo:** emails.py:línea
- **Problema:** LIMIT 200 hardcodeado
- **Fix:** Agregar parámetros page/size

### [MEDIUM] Health check no verifica DB
- **Archivo:** main.py:línea
- **Problema:** Solo retorna {"status": "ok"}
- **Fix:** Agregar SELECT 1 a PostgreSQL

## Recomendaciones
1. Agregar paginación estándar (page, size, total)
2. Implementar rate limiting con `slowapi`
3. Crear schema de error consistente
4. Agregar versionado de API (/api/v1/)
```

## Notes

- FastAPI procesa rutas en orden de definición - las más específicas primero
- `response_model` en FastAPI ayuda a documentar y validar respuestas
- `@app.exception_handler` puede centralizar manejo de errores
- Para rate limiting, `slowapi` es la librería más popular para FastAPI
