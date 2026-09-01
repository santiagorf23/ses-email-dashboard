---
name: docs-sync
description: Verifica que la documentación (README.md, schemas, API docs) coincida con el código fuente real del proyecto
model: sonnet
allowed-tools: [Read, Grep, Glob, Bash, Edit]
---

# Docs Sync Skill

## Goal

Detectar discrepancias entre la documentación existente y el código fuente real, y actualizar la documentación para que refleje fielmente el estado actual del proyecto.

## When to use

- Después de cambios significativos en el esquema de BD
- Después de agregar/quitar columnas o tablas
- Cuando se modifican endpoints de la API
- Antes de releases para asegurar docs actualizadas
- Cuando nuevos desarrolladores reportan confusión con la docs

## Steps

### 1. Auditar README.md vs Código Real

```bash
# Verificar estructura de directorios mencionada en README
rg -n "├──|└──" README.md | head -30

# Comparar con estructura real
find . -maxdepth 3 -type f ! -path "./.git/*" ! -path "*/venv/*" ! -path "*/__pycache__/*" | sort
```

### 2. Auditar Schema de BD vs Documentación

```bash
# Extraer schema documentado del README
rg -n "CREATE TABLE|VARCHAR|INTEGER|BOOLEAN|JSONB|TIMESTAMP" README.md

# Comparar con init.sql real
rg -n "CREATE TABLE|VARCHAR|INTEGER|BOOLEAN|JSONB|TIMESTAMP" database/init.sql
```

### 3. Verificar Discrepancias Específicas

**Problema conocido: columna `status`**
- README dice: "La tabla email_send NO tiene columna status"
- init.sql tiene: `status TEXT NOT NULL DEFAULT 'sent'`
- Código la usa: `es.status` en queries

**Problema conocido: columnas faltantes en init.sql**
- README muestra: `has_attachments BOOLEAN`, `attachments JSONB`
- init.sql NO las tiene
- Código las consulta: `es.has_attachments`, `es.attachments`

### 4. Verificar Endpoints de API

```bash
# Extraer endpoints documentados
rg -n "GET|POST|PUT|DELETE|PATCH" README.md

# Comparar con endpoints reales
rg -n "@app\.\(get\|post\|put\|delete\|patch\)" backend/routers/ --type py
```

### 5. Verificar Variables de Entorno

```bash
# Variables documentadas
rg -n "DATABASE_URL|SECRET_KEY|ADMIN_" README.md

# Variables reales en código
rg -n "os\.getenv\(" backend/ --type py

# Variables en .env.example
cat backend/.env.example
```

### 6. Generar Script de Sincronización

Crear script que detecte automáticamente las discrepancias:

```bash
#!/bin/bash
# scripts/check-docs-sync.sh

echo "=== Docs Sync Checker ==="

# 1. Verificar columnas documentadas vs reales
echo ""
echo "--- Columnas en README ---"
rg -n "has_attachments|attachments" README.md

echo ""
echo "--- Columnas en init.sql ---"
rg -n "has_attachments|attachments" database/init.sql

# 2. Verificar status column
echo ""
echo "--- Status en README ---"
rg -n "status" README.md | grep -i "no.*tiene\|NO.*column"

echo ""
echo "--- Status en init.sql ---"
rg -n "status" database/init.sql

# 3. Verificar endpoints
echo ""
echo "--- Endpoints en README ---"
rg -n "GET /api/|POST /api/" README.md

echo ""
echo "--- Endpoints en código ---"
rg -n "@app\.\(get\|post\)" backend/routers/ --type py
```

### 7. Actualizar Documentación

Para cada discrepancia encontrada, actualizar README.md con la información correcta del código fuente.

## Validation

- [ ] Estructura de directorios en README = estructura real
- [ ] Schema documentado = init.sql
- [ ] Endpoints documentados = endpoints reales
- [ ] Variables de entorno documentadas = variables reales
- [ ] Tipos de datos correctos en documentación

## Output

```markdown
# Docs Sync Report

## Discrepancias Encontradas

### [HIGH] Columna status documentada incorrectamente
- **Archivo:** README.md:línea
- **Dice:** "La tabla email_send NO tiene columna status"
- **Real:** init.sql define `status TEXT NOT NULL DEFAULT 'sent'`
- **Acción:** Actualizar README

### [MEDIUM] Columnas faltantes en init.sql
- **Archivo:** database/init.sql
- **Falta:** has_attachments, attachments
- **Impacto:** Backend fallará al consultar estas columnas
- **Acción:** Agregar columnas a init.sql

## Cambios Realizados
1. README.md actualizado con schema correcto
2. init.sql actualizado con columnas faltantes
```

## Notes

- Este skill es ESPECIALMENTE importante para este proyecto que tiene discrepancias conocidas
- Siempre verificar contra el código fuente, no contra lo que "se cree que es"
- Las discrepancies en schemas de BD pueden causar errores en runtime
- Documentar cada cambio para mantener historial de sincronización
