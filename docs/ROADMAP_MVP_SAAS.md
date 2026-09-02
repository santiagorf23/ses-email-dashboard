# Roadmap MVP SaaS — Prioridades Inmediatas

## Contexto

Convertir el SES Dashboard actual en un producto SaaS monetizable. Las 3 prioridades inmediatas son:

1. **Webhook Receiver** — Sin esto no hay data entrante automatizada
2. **Multi-Tenant** — Sin esto no puedes vender a múltiples clientes
3. **Onboarding Wizard** — Sin esto los usuarios abandonan al no saber configurar

---

## Tarea 1: Webhook Receiver (`/api/webhooks/ses`)

### Objetivo
Recibir eventos de AWS SES automáticamente via SNS, sin que el usuario tenga que importar CSVs o hacer polling.

### Archivos a crear/modificar

| Archivo | Acción |
|---------|--------|
| `backend/routers/webhooks.py` | **NUEVO** — Endpoint POST `/api/webhooks/ses` |
| `backend/main.py` | Agregar router de webhooks |
| `backend/services/sns_parser.py` | **NUEVO** — Parsear notificaciones SNS |
| `database/init.sql` | Agregar tabla `webhook_logs` para auditoría |
| `backend/models.py` | Agregar schemas para SNS notifications |

### Lógica del webhook

```
1. AWS SES envía notificación SNS a POST /api/webhooks/ses
2. SNS envía SubscribeConfirmation → responder con GET al link
3. SNS envía Notification → parsear JSON:
   - MessageType = "Notification"
   - Message.mail.commonHeaders.subject → subject
   - Message.mail.commonHeaders.from → email_from
   - Message.mail.commonHeaders.to → email_to
   - Message.mail.messageId → message_id (buscar en email_send)
   - Message.notification.bounce/complaint/delivery → tipo de evento
4. Insertar en email_events con tenant_id
5. Retornar 200 OK rápido (< 1s)
```

### Estructura del mensaje SNS

```json
{
  "Type": "Notification",
  "MessageId": "uuid",
  "TopicArn": "arn:aws:sns:region:account:topic",
  "Subject": "Amazon SES Email Event Notification",
  "Message": {
    "mail": {
      "messageId": "ses-message-id",
      "timestamp": "2024-01-01T00:00:00Z",
      "source": "sender@domain.com",
      "commonHeaders": {
        "from": ["sender@domain.com"],
        "to": ["recipient@example.com"],
        "subject": "Test email"
      }
    },
    "notification": {
      "type": "Bounce",
      "bounceType": "Permanent",
      "bounceSubType": "NoEmail",
      "bouncedRecipients": [
        {"emailAddress": "recipient@example.com", "action": "failed", "status": "550", "diagnosticCode": "..."}
      ]
    }
  }
}
```

### Endpoints necesarios

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/api/webhooks/ses` | Recibir eventos SNS |
| `GET` | `/api/webhooks/ses` | Confirmar suscripción SNS |
| `POST` | `/api/webhooks/ses/subscribe` | Endpoint para suscribir SNS topic |

### Validaciones
- Verificar firma SNS (opcional pero recomendado)
- Rate limiting por IP de AWS SNS
- Log de todos los webhooks recibidos (auditoría)
- Manejar duplicates (SNS puede reintentar)

---

## Tarea 2: Multi-Tenant

### Objetivo
Cada usuario ve SOLO sus correos. Separación completa de datos.

### Archivos a crear/modificar

| Archivo | Acción |
|---------|--------|
| `database/migrations/001_multi_tenant.sql` | **NUEVO** — Schema multi-tenant |
| `backend/middleware/tenant.py` | **NUEVO** — Middleware para extraer tenant del JWT |
| `backend/models/tenant.py` | **NUEVO** — Modelo de tenant |
| `backend/routers/tenants.py` | **NUEVO** — CRUD de tenants |
| `backend/routers/auth.py` | Modificar login para incluir tenant_id en JWT |
| `backend/db/database.py` | Modificar connection para setear `app.current_tenant` |
| `backend/routers/emails.py` | Agregar filtro automático por tenant |
| `backend/routers/health.py` | Agregar métricas por tenant |

### Schema multi-tenant

```sql
-- Tabla de tenants
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    aws_access_key_enc TEXT,        -- encriptado con AES-256
    aws_secret_key_enc TEXT,        -- encriptado con AES-256
    aws_region TEXT DEFAULT 'us-east-1',
    aws_sns_topic_arn TEXT,
    plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'business', 'enterprise')),
    plan_limits JSONB DEFAULT '{"max_emails": 1000, "max_domains": 1, "retention_days": 7}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agregar tenant_id a tablas existentes
ALTER TABLE email_send ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE email_events ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE email_block ADD COLUMN tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;

-- Índices
CREATE INDEX idx_email_send_tenant ON email_send(tenant_id, created_at DESC);
CREATE INDEX idx_email_events_tenant ON email_events(tenant_id, created_at DESC);
CREATE INDEX idx_email_block_tenant ON email_block(tenant_id);

-- RLS (Row Level Security)
ALTER TABLE email_send ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_block ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_send ON email_send
    USING (tenant_id = current_setting('app.current_tenant')::int);
CREATE POLICY tenant_isolation_events ON email_events
    USING (tenant_id = current_setting('app.current_tenant')::int);
CREATE POLICY tenant_isolation_block ON email_block
    USING (tenant_id = current_setting('app.current_tenant')::int);

-- Tabla de usuarios (para multi-usuario futuro)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'admin' CHECK (role IN ('admin', 'viewer', 'analyst')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
```

### JWT actualizado

```python
# Payload del JWT
{
    "sub": "user@email.com",
    "tenant_id": 123,
    "role": "admin",
    "exp": 1234567890
}
```

### Middleware de tenant

```python
# En cada request:
# 1. Extraer JWT del header Authorization
# 2. Validar JWT y extraer tenant_id
# 3. Ejecutar: SET app.current_tenant = '{tenant_id}'
# 4. RLS filtra automáticamente
```

### Planes y límites

| Plan | Emails/mes | Dominios | Retención | Alertas | API |
|------|-----------|----------|-----------|---------|-----|
| Free | 1,000 | 1 | 7 días | No | No |
| Pro | 50,000 | 5 | 90 días | Sí | Básica |
| Business | Ilimitado | Ilimitado | 1 año | Sí | Completa |
| Enterprise | Custom | Custom | Custom | Sí | Completa + Webhooks |

---

## Tarea 3: Onboarding Wizard

### Objetivo
Guiar al usuario desde el registro hasta recibir su primer evento de email.

### Archivos a crear/modificar

| Archivo | Acción |
|---------|--------|
| `frontend/onboarding.html` | **NUEVO** — Página de onboarding |
| `frontend/js/onboarding.js` | **NUEVO** — Lógica del wizard |
| `frontend/css/onboarding.css` | **NUEVO** — Estilos del wizard |
| `backend/routers/onboarding.py` | **NUEVO** — Endpoints de onboarding |
| `frontend/index.html` | Agregar redirect a onboarding si tenant nuevo |

### Pasos del wizard

#### Paso 1: Welcome
- Nombre del equipo/proyecto
- Dominio de email principal (ej: `empresa.com`)
- Botón "Comenzar"

#### Paso 2: AWS Setup
- Instrucciones paso a paso para crear IAM user
- Permisos necesarios: `ses:SendEmail`, `ses:SendRawEmail`, `sns:CreateTopic`, `sns:Subscribe`
- Formulario para ingresar Access Key + Secret Key
- Botón "Verificar credenciales" (llamada a AWS STS GetCallerIdentity)

#### Paso 3: Verify Domain
- Instrucciones para agregar registros DNS:
  - TXT: `amazonses:verification-code`
  - CNAME: `feedback-smtp.us-east-1.amazonses.com` → `bounce.example.com`
  - CNAME: `abstractmethod._domainkey.us-east-1.amazonses.com` → dkim.amazonses.com
- Botón "Verificar dominio" (llamada a SES VerifyDomainIdentity)
- Auto-refresh cada 5 segundos hasta verificado

#### Paso 4: Configure Webhook
- URL del webhook: `https://tu-dominio.com/api/webhooks/ses`
- Instrucciones para suscribir SNS:
  ```bash
  aws sns subscribe --topic-arn arn:aws:sns:us-east-1:123456789:ses-events \
    --protocol https \
    --notification-endpoint https://tu-dominio.com/api/webhooks/ses
  ```
- Botón "Suscribir SNS" (llamada automática si tiene credenciales)
- Botón "Confirmar suscripción" (verificar que llegó confirmación)

#### Paso 5: Test
- Botón "Enviar email de prueba" (envía a email del usuario)
- Esperar evento (polling cada 2 segundos por 30 segundos)
- Si llega → "¡Funciona! Tu dashboard está listo"
- Si no llega → troubleshooting tips

#### Paso 6: Dashboard
- Redirect al dashboard principal
- Tooltip de bienvenida explicando las métricas

### UX del wizard

```
┌─────────────────────────────────────────────────┐
│  [1] Welcome    [2] AWS    [3] Domain    [4] Webhook    [5] Test │
│  ─────●──────────────────────────────────────────────○────○────○ │
└─────────────────────────────────────────────────┘
```

- Cada paso se guarda progresivamente
- Se puede volver atrás
- Si el usuario cierra el navegador, puede continuar después
- Skip allowed (para usuarios avanzados)

---

## Orden de Implementación

1. **Primero: Multi-Tenant** (porque todo lo demás depende de esto)
2. **Segundo: Webhook Receiver** (para recibir data)
3. **Tercero: Onboarding Wizard** (para guiar al usuario)

### Estimación de tiempo

| Tarea | Días estimados |
|-------|----------------|
| Multi-Tenant (schema + middleware + auth) | 5-7 días |
| Webhook Receiver (endpoint + SNS parser) | 3-4 días |
| Onboarding Wizard (frontend + backend) | 4-5 días |
| Testing y fixes | 2-3 días |
| **Total** | **14-19 días** |

---

## Criterios de Aceptación

### Webhook Receiver
- [ ] Endpoint POST `/api/webhooks/ses` retorna 200 OK
- [ ] Endpoint GET `/api/webhooks/ses` maneja confirmación SNS
- [ ] Eventos SNS se insertan correctamente en `email_events`
- [ ] Soporta Bounce, Complaint, Delivery, Open, Click
- [ ] Maneja duplicates sin duplicar eventos
- [ ] Rate limiting funciona correctamente
- [ ] Logging de todos los webhooks recibidos

### Multi-Tenant
- [ ] Tabla `tenants` creada con schema correcto
- [ ] `tenant_id` agregado a email_send, email_events, email_block
- [ ] RLS policies funcionando (cada tenant solo ve sus datos)
- [ ] JWT incluye `tenant_id`
- [ ] Middleware setea `app.current_tenant` en cada request
- [ ] Login retorna JWT con tenant_id
- [ ] Queries de emails filtran por tenant automáticamente

### Onboarding Wizard
- [ ] 5 pasos funcionando end-to-end
- [ ] Verificación de credenciales AWS funciona
- [ ] Verificación de dominio funciona
- [ ] Suscripción SNS funciona
- [ ] Email de prueba funciona
- [ ] Progreso se guarda (puede continuar después)
- [ ] Skip allowed para usuarios avanzados
