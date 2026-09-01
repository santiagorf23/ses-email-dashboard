# SES Mail Dashboard - Agents & Skills

Este directorio contiene los agents y skills para asegurar calidad, seguridad y buenas prácticas en el proyecto.

## Estructura

```
.agents/
├── skills/
│   ├── security-review/    # Auditoría de seguridad
│   ├── code-quality/       # Linting y análisis de código
│   ├── test-generator/     # Generación de tests
│   ├── docker-audit/       # Auditoría de Docker
│   ├── docs-sync/          # Sincronización de documentación
│   └── api-review/         # Revisión de diseño de API
├── agents/
│   ├── quality-guardian.md # Guardián global de calidad
│   ├── security-agent.md   # Agente de seguridad
│   ├── code-reviewer.md    # Agente de revisión de código
│   └── infra-reviewer.md   # Agente de infraestructura
└── docs/
    └── skills_agents_catalog.md  # Catálogo completo
```

## Uso Rápido

### Para cualquier cambio de código:

```bash
# 1. Implementar el cambio
# 2. Verificar calidad
cat .agents/agents/quality-guardian.md  # Seguir el checklist
```

### Para auditoría completa:

```bash
# Revisar skills disponibles
cat .agents/docs/skills_agents_catalog.md
```

## Reglas del Proyecto

1. **SIEMPRE** ejecutar quality-guardian antes de commit
2. **NUNCA** ignorar hallazgos de seguridad críticos
3. **USAR** skills existentes antes de crear código ad-hoc
4. **ACTUALIZAR** este catálogo cuando se creen nuevos skills/agents
