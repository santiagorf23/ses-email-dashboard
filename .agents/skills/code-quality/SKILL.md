---
name: code-quality
description: Ejecuta linting, análisis de tipo, formato y detecta code smells en Python y JavaScript
model: sonnet
allowed-tools: [Read, Grep, Glob, Bash, Edit]
---

# Code Quality Skill

## Goal

Ejecutar herramientas de análisis estático para detectar errores de tipo, code smells, código muerto, duplicación y problemas de formato en el código fuente.

## When to use

- Antes de cada commit para validar calidad
- Durante code review para detectar problemas automáticamente
- Como parte de CI/CD pipeline
- Al iniciar un plan de refactorización

## Steps

### 1. Instalación de Herramientas (si no existen)

```bash
# Python
pip install ruff mypy bandit

# JavaScript (si hay package.json)
npm install --save-dev eslint
```

### 2. Análisis de Código Python

```bash
# Ruff - Linting rápido (reemplaza flake8, isort, etc.)
ruff check backend/ --output-format=concise

# Ruff - Verificar formato
ruff format --check backend/

# Mypy - Análisis de tipos
cd backend && mypy . --ignore-missing-imports

# Bandit - Análisis de seguridad estática
bandit -r backend/ -f json -o bandit-report.json
```

### 3. Análisis de Código JavaScript

```bash
# ESLint (si está configurado)
cd frontend && npx eslint js/

# Buscar console.log en producción
rg -n "console\.(log|warn|error)" frontend/

# Buscar variables no usadas
rg -n "^\s*(const|let|var)\s+\w+" frontend/js/ | head -20
```

### 4. Detección de Code Smells

```bash
# Funciones muy largas (>50 líneas)
rg -n "^def |^async def " backend/ --type py -l | xargs wc -l | sort -rn | head -10

# Archivos muy grandes (>500 líneas)
find . -name "*.py" -o -name "*.js" -o -name "*.html" | xargs wc -l | sort -rn | head -10

# Código duplicado (buscar patrones similares)
rg -n "except Exception:" backend/ --type py

# Bare except
rg -n "except:" backend/ --type py
```

### 5. Análisis de Complejidad

```bash
# Instalar radon (complejidad ciclomática)
pip install radon

# Calcular complejidad ciclomática
radon cc backend/ -a -nc
```

### 6. Generación de Reporte

Crear `QUALITY_REPORT.md` con:
- Resumen de issues por severidad
- Archivos con más problemas
- Métricas de complejidad
- Recomendaciones prioritarias

## Validation

- [ ] Ruff ejecutado sin errores críticos
- [ ] Mypy ejecutado (warnings documentados)
- [ ] Bandit reporte generado
- [ ] Code smells identificados
- [ ] Reporte de calidad generado

## Output

```markdown
# Code Quality Report

## Resumen
- Errores de linting: X
- Warnings: X
- Issues de seguridad: X
- Code smells: X

## Por Archivo
| Archivo | Errores | Warnings | Líneas |
|---------|---------|----------|--------|

## Top Issues
1. [ERROR] ...
2. [WARN] ...
```

## Notes

- Ruff es 10-100x más rápido que flake8/pylint
- Bandit detecta issues de seguridad que Ruff no cubre
- Mypy en modo `--ignore-missing-imports` es menos estricto pero más práctico
- Para este proyecto (sin tests), el foco está en detección, no en fix
