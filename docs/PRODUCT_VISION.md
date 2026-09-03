# SES Dashboard — Visión de Producto Digital

## Estado Actual

Sistema funcional de monitoreo de emails transaccionales via AWS SES:

- Backend: Python FastAPI + PostgreSQL 16
- Frontend: HTML/CSS/JS vanilla, responsive, dark/light theme
- Features: Tracking de correos, eventos (send/delivery/bounce/complaint/open/click), bloqueados, analytics con charts, PDF export
- Infraestructura: Docker, Makefile, nginx, rate limiting, JWT auth

---

## 1. Modelo de Monetización

| Tier                 | Precio  | Target                                                      |
| -------------------- | ------- | ----------------------------------------------------------- |
| **Free**       | $0/mes  | Hasta 1,000 correos/mes, 1 dominio, 7 días de datos        |
| **Pro**        | $29/mes | 50,000 correos/mes, 5 dominios, 90 días, alerts            |
| **Business**   | $99/mes | Ilimitado, dominios ilimitados, 1 año datos, API, webhooks |
| **Enterprise** | Custom  | Multi-tenant, SSO, SLA, soporte dedicado                    |

---

## 2. Features de Alto Valor

### 🔴 Críticas (MVP Monetizable)

| Feature                              | Descripción                                                                     | Impacto                                   |
| ------------------------------------ | -------------------------------------------------------------------------------- | ----------------------------------------- |
| **Multi-tenant**               | Cada usuario ve SOLO sus correos. Separación de datos por`api_key` de AWS SES | Requisito para SaaS                       |
| **Onboarding wizard**          | Guiar al usuario a configurar su AWS SES, verificar dominio, configurar webhooks | Reduce fricción de entrada               |
| **Webhook receiver endpoint**  | Endpoint`/api/webhooks/ses` para recibir eventos SNS de SES automáticamente   | Core del producto — sin esto no hay data |
| **Alertas de deliverability**  | Notificar cuando bounce rate > 5%, complaint rate > 0.1%, o bounce súbito       | Evita que el usuario sea baneado de SES   |
| **Reportes de deliverability** | Score de reputación por dominio, tendencias, comparativas temporales            | Valor analítico principal                |

### 🟡 Diferenciadoras (Pro/Business)

| Feature                                | Descripción                                                                       | Impacto                           | Estado |
| -------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------- | ------ |
| **Email verification**           | Verificar lista de correos antes de enviar (validación DNS, disposable detection) | Ahorra dinero en envíos fallidos | ⏳ Pendiente |
| **A/B testing de asuntos**       | Comparar open rates entre variantes de subject line                                | Optimización de campañas        | ⏳ Pendiente |
| **Heatmap de engagement**        | Qué horarios/días tienen mejor open rate                                         | Mejora timing de envíos          | ⏳ Pendiente |
| **Integración directa con SES** | Enviar correos desde el dashboard via SES API                                      | Todo-en-uno                       | ⏳ Pendiente |
| **Slack/Email alerts**           | Recibir notificaciones de bounce/complaint en Slack o email                        | Monitoreo pasivo                  | ✅ Completado |
| **Exportación de reportes**     | PDF/CSV programados (diario/semanal/mensual)                                       | Para managers y equipos           | ✅ Completado |

### 🟢 Premium (Enterprise)

| Feature                           | Descripción                                  | Impacto                       |
| --------------------------------- | --------------------------------------------- | ----------------------------- |
| **Multi-usuario con roles** | Admin, viewer, analyst con permisos distintos | Para equipos                  |
| **API pública**            | REST API para integraciones externas          | Para desarrolladores          |
| **White-label**             | Customizar logo, colores, dominio             | Para agencias que lo revenden |
| **SSO (SAML/OIDC)**         | Login corporativo                             | Requisito enterprise          |
| **Audit log**               | Quién hizo qué y cuándo                    | Compliance                    |

---

## 3. Arquitectura para SaaS

```
┌─────────────────────────────────────────────────┐
│                  FRONTEND (SPA)                 │
│  Next.js o mantener vanilla + mejorar routing   │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│                  API GATEWAY                    │
│  Rate limiting por tenant, JWT validation       │
└──────────────────────┬──────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐
│   Auth API   │ │  Data API │ │ Webhook   │
│  (login,     │ │ (emails,  │ │ Receiver  │
│   tenants)   │ │  events)  │ │ (SES SNS) │
└──────────────┘ └───────────┘ └───────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
              ┌────────▼────────┐
              │   PostgreSQL    │
              │  (schema/tent)  │
              └─────────────────┘
```

---

## 4. Cambio de Base de Datos para Multi-Tenant

```sql
-- Nuevo: tabla de tenants
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    aws_access_key TEXT,        -- encriptado
    aws_secret_key TEXT,        -- encriptado
    aws_region TEXT DEFAULT 'us-east-1',
    plan TEXT DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Modificar: agregar tenant_id a todas las tablas
ALTER TABLE email_send ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);
ALTER TABLE email_events ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);
ALTER TABLE email_block ADD COLUMN tenant_id INTEGER REFERENCES tenants(id);

-- RLS (Row Level Security) para aislamiento
ALTER TABLE email_send ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON email_send
    USING (tenant_id = current_setting('app.current_tenant')::int);
```

---

## 5. Monetización Adicional

| Fuente                                   | Descripción                                                                  |
| ---------------------------------------- | ----------------------------------------------------------------------------- |
| **Marketplace de templates**       | Templates de email transaccional que los usuarios pueden comprar/usar         |
| **Consultoría de deliverability** | Servicio premium de revisión de configuración SES                           |
| **Integraciones**                  | Cobrar extra por integraciones con HubSpot, Mailchimp, etc.                   |
| **Data insights anonymizados**     | Reportes de tendencias de deliverability de la industria (sin datos privados) |

---

## 6. Roadmap

| Fase                            | Tiempo      | Features                                                    |
| ------------------------------- | ----------- | ----------------------------------------------------------- |
| **Fase 1: MVP SaaS**      | 4-6 semanas | Multi-tenant, webhook receiver, onboarding, auth por tenant |
| **Fase 2: Alerts**        | 2 semanas   | Alertas de bounce/complaint, email notifications            |
| **Fase 3: Monetización** | 2 semanas   | Integración Stripe, tiers, limits por plan                 |
| **Fase 4: Pro features**  | 4 semanas   | API pública, reportes programados, A/B testing             |
| **Fase 5: Enterprise**    | 4 semanas   | Multi-usuario, roles, SSO, white-label                      |

---

## 7. Diferenciadores vs Competencia

| Competencia                  | Ventaja del producto                                                          |
| ---------------------------- | ----------------------------------------------------------------------------- |
| **Mailgun**            | Ellos son ESP, nosotros somos monitoring puro — sin conflicto de interés    |
| **SendGrid Analytics** | Solo muestran data de su plataforma, nosotros soportamos cualquier SES setup  |
| **Litmus**             | Enfocado en testing de emails, no en deliverability en producción            |
| **Custom dashboards**  | La mayoría construyen uno interno — nosotros ofrecemos SaaS listo para usar |

---

## 8. Prioridades Inmediatas

### Fase 1: MVP SaaS (Semanas 1-6)

#### 8.1 Webhook Receiver (`/api/webhooks/ses`)

```python
# POST /api/webhooks/ses
# Recibe notificaciones SNS de AWS SES
# Parsea MessageType: Notification (bounce/complaint/delivery) + Bounce/Complaint sub-types
# Inserta en email_events con tenant_id
```

**Flujo:**

1. AWS SES envía notificación SNS a tu endpoint
2. SNS envía `SubscribeConfirmation` → responder con GET al link de confirmación
3. SNS envía `Notification` → parsear JSON, extraer evento, insertar en DB
4. Webhook retorna 200 OK rápido (< 1s) para evitar retries de SNS

#### 8.2 Multi-Tenant

**Schema de BD:**

- `tenants` table: id, name, slug, aws_access_key (encrypted), aws_secret_key (encrypted), aws_region, plan, created_at
- Agregar `tenant_id` FK a: email_send, email_events, email_block
- RLS policies para aislamiento automático
- Middleware en FastAPI: leer tenant del JWT, setear `app.current_tenant`

**Auth:**

- Login → verificar credenciales → crear JWT con `tenant_id`
- Cada query filtra por `tenant_id` automáticamente via RLS

#### 8.3 Onboarding Wizard

**Pantallas:**

1. **Welcome** → Nombre del equipo, dominio de email
2. **AWS Setup** → Instrucciones para crear IAM user con permisos SES
3. **Verify Domain** → Instrucciones para agregar TXT/CNAME records
4. **Configure Webhook** → Copiar endpoint URL, instrucciones para suscribir SNS
5. **Test** → Enviar email de prueba, verificar que llega el evento

#### 8.4 Alertas de Deliverability

**Reglas de alerta:**

- Bounce rate > 5% en última hora → alerta crítica
- Complaint rate > 0.1% → alerta crítica
- Bounce rate > 3% → alerta warning
- Spike de bounces (más de 10 en 5 minutos) → alerta crítica
- Dominio nuevo sin eventos → verificar configuración

**Canales:**

- In-app notification (toast/banner)
- Email al admin del tenant
- Webhook a URL configurada (Slack, Discord, etc.)

#### 8.5 Reportes de Deliverability

**Métricas principales:**

- **Deliverability Score**: 0-100 basado en bounce rate, complaint rate, engagement
- **Bounce rate trend**: Gráfico de bounce % por día/semana
- **Top bounce reasons**: Clasificación de bounces (hard/soft, reason)
- **Engagement timeline**: Opens/clicks por día
- **Domain reputation**: Score por dominio de envío

---

### Fase 2: Alerts (Semanas 7-8)

- Alertas configurables por usuario (umbrales personalizados)
- Historial de alertas
- Integración con email (SendGrid/SES para enviar alertas)
- Webhook alerts a Slack/Discord/Teams

---

### Fase 3: Monetización (Semanas 9-10)

- Integración Stripe para pagos
- Limitar features por plan (rate limits, retention, domains)
- Portal de billing (ver plan, cambiar, ver factura)
- Trials de 14 días para Pro/Business

---

### Fase 4: Pro Features (Semanas 11-14)

- API pública con API keys por tenant
- Reportes programados (PDF/CSV por email)
- A/B testing de subject lines
- Heatmap de engagement (mejores horarios)
- Email verification (validar listas antes de enviar)

---

### Fase 5: Enterprise (Semanas 15-18)

- Multi-usuario con roles (admin, viewer, analyst)
- SSO (SAML/OIDC)
- White-label (custom logo, colores, dominio)
- Audit log
- SLA monitoring
- Soporte dedicado

---

## 9. Stack Tecnológico Recomendado

| Capa      | Actual              | Recomendado para SaaS        |
| --------- | ------------------- | ---------------------------- |
| Frontend  | Vanilla HTML/CSS/JS | Next.js (SSR, routing, auth) |
| Backend   | FastAPI             | FastAPI (mantener)           |
| DB        | PostgreSQL 16       | PostgreSQL + RLS             |
| Auth      | JWT simple          | JWT + refresh tokens         |
| Pagos     | Ninguno             | Stripe                       |
| Email     | SES directo         | SES + SNS webhooks           |
| Monitoreo | Ninguno             | Sentry + Prometheus          |
| CI/CD     | Manual              | GitHub Actions               |

---

## 10. Métricas de Éxito

| Métrica                        | Target MVP | Target 6 meses |
| ------------------------------- | ---------- | -------------- |
| Usuarios registrados            | 100        | 1,000          |
| Usuarios activos mensuales      | 30         | 300            |
| MRR (Monthly Recurring Revenue) | $500       | $5,000         |
| Churn rate                      | < 10%      | < 5%           |
| NPS (Net Promoter Score)        | > 30       | > 50           |

---

## 11. Riesgos y Mitigaciones

| Riesgo                         | Mitigación                                             |
| ------------------------------ | ------------------------------------------------------- |
| AWS SES pricing changes        | Monitorear, mantener compatibilidad con otros providers |
| Competencia de grandes players | Enfocar en nicho (SES users, no ESP general)            |
| Security breach de credentials | Encriptar AWS keys, RLS estricto, audit log             |
| Escalabilidad de DB            | Partitioning por fecha, archival de datos antiguos      |
| Soporte al usuario             | Documentación completa, chatbot, community forum       |
