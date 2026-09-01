---
name: security-review
description: Revisa el código en busca de vulnerabilidades de seguridad, secrets hardcodeados, inyección SQL, XSS y dependencias con CVEs conocidos
model: sonnet
allowed-tools: [Read, Grep, Glob, Bash]
---

# Security Review Skill

## Goal

Realizar una auditoría de seguridad completa del código fuente, detectando vulnerabilidades críticas como inyección SQL, secrets hardcodeados, XSS, dependencias vulnerables y mala configuración de infraestructura.

## When to use

- Antes de cada release o deploy a producción
- Después de cambios que toquen autenticación, manejo de inputs o red
- Cuando se detectan problemas de seguridad reportados
- Periódicamente como parte de mantenimiento preventivo

## Steps

### 1. Escaneo de Secrets Hardcodeados

Buscar en todo el código patrones de secrets:

```bash
# Buscar secrets en código fuente
rg -n "(SECRET_KEY|PASSWORD|API_KEY|TOKEN)\s*=\s*['\"]" --type py
rg -n "(secret|password|token|key)\s*[:=]\s*['\"]" --type js

# Buscar archivos .env committeados
git ls-files | grep -E "\.env$"

# Buscar credentials en docker-compose
rg -n "(password|secret|key)\s*:" docker-compose.yml
```

### 2. Detección de SQL Injection

Buscar interpolación de variables en queries SQL:

```bash
# Buscar f-strings en queries SQL
rg -n "f['\"].*SELECT|f['\"].*INSERT|f['\"].*UPDATE|f['\"].*DELETE" --type py

# Buscar format() en queries
rg -n "\.format\(.*\).*SELECT|\.format\(.*\).*INSERT" --type py

# Buscar concatenación en queries
rg -n "\+.*SELECT|\+.*INSERT|\+.*WHERE" --type py
```

### 3. Detección de XSS

Buscar uso de innerHTML, eval, document.write sin sanitización:

```bash
# Buscar innerHTML sin esc()
rg -n "innerHTML\s*=" --type js

# Buscar eval()
rg -n "eval\s*\(" --type js

# Buscar document.write
rg -n "document\.write" --type js

# Buscar interpolación en onclick
rg -n "onclick=.*\$\{" --type js
```

### 4. Auditoría de Dependencias

```bash
# Verificar vulnerabilidades en Python
pip install pip-audit
pip-audit -r backend/requirements.txt

# Verificar versiones sin pinning
rg -n "^[a-z]" backend/requirements.txt | grep -v "=="
```

### 5. Revisión de Configuración de Seguridad

Verificar:
- CORS configurado con `allow_origins=["*"]`
- Health check no verifica DB
- Sin rate limiting en endpoints de auth
- Tokens almacenados en localStorage
- Sin Content Security Policy (CSP)

### 6. Auditoría de Docker

```bash
# Verificar si .dockerignore existe
ls -la .dockerignore

# Verificar si Dockerfile usa USER directive
rg -n "^USER" backend/Dockerfile

# Verificar secrets en docker-compose
rg -n "(password|secret|key)\s*:" docker-compose.yml
```

## Validation

- [ ] Todos los secrets hardcodeados identificados
- [ ] SQL injection vectors detectados y documentados
- [ ] XSS vulnerabilities catalogadas
- [ ] Dependencias vulnerables listadas
- [ ] Configuración Docker auditada

## Output

Generar `SECURITY_REVIEW.md` en la raíz del proyecto con:

```markdown
# Security Review Report

## Resumen Ejecutivo
- Críticos: X
- Altos: X
- Medios: X
- Bajos: X

## Vulnerabilidades Encontradas

### [CRITICAL] Título de la vulnerabilidad
- **Archivo:** ruta/archivo.py:línea
- **Descripción:** ...
- **Impacto:** ...
- **Fix sugerido:** ...

## Dependencias Vulnerables
| Paquete | Versión | CVE | Severidad |
|---------|---------|-----|-----------|

## Recomendaciones
1. ...
2. ...
```

## Notes

- Este skill NO modifica código, solo reporta hallazgos
- Los hallazgos críticos deben resolverse antes de cualquier deploy
- Usar junto con el agent `security-agent` para fix automático de issues simples
