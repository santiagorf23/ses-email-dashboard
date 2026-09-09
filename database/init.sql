-- ============================================================
-- SES Dashboard — Schema e índices optimizados
-- ============================================================

-- Tabla principal de correos enviados
CREATE TABLE IF NOT EXISTS email_send (
    id          SERIAL PRIMARY KEY,
    message_id  TEXT NOT NULL UNIQUE,
    email_to    TEXT NOT NULL,
    email_from  TEXT NOT NULL,
    subject     TEXT NOT NULL,
    content     TEXT,
    mime_type   TEXT NOT NULL DEFAULT 'text/html',
    status      TEXT NOT NULL DEFAULT 'sent',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla de eventos SNS (send, delivery, bounce, complaint, open, click)
CREATE TABLE IF NOT EXISTS email_events (
    id            SERIAL PRIMARY KEY,
    email_send_id INTEGER NOT NULL REFERENCES email_send(id) ON DELETE CASCADE,
    event_type    TEXT NOT NULL,
    event_data    JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla de correos bloqueados (hard bounces y complaints)
CREATE TABLE IF NOT EXISTS email_block (
    id         SERIAL PRIMARY KEY,
    email      TEXT NOT NULL UNIQUE,
    reason     TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Índices para mejorar performance de las queries del dashboard
-- ============================================================

-- Listado ordenado por fecha (más usado)
CREATE INDEX IF NOT EXISTS idx_email_send_created_at
    ON email_send (created_at DESC);

-- Filtro por status
CREATE INDEX IF NOT EXISTS idx_email_send_status
    ON email_send (status);

-- Búsqueda por destinatario
CREATE INDEX IF NOT EXISTS idx_email_send_email_to
    ON email_send (email_to);

-- Búsqueda por message_id (SES callback)
CREATE INDEX IF NOT EXISTS idx_email_send_message_id
    ON email_send (message_id);

-- Índice compuesto para filtros combinados frecuentes
CREATE INDEX IF NOT EXISTS idx_email_send_status_created
    ON email_send (status, created_at DESC);

-- Eventos por correo
CREATE INDEX IF NOT EXISTS idx_email_events_send_id
    ON email_events (email_send_id, created_at ASC);

-- Índice para buscar eventos por tipo (ej: todos los bounces)
CREATE INDEX IF NOT EXISTS idx_email_events_type
    ON email_events (event_type);

-- Búsqueda full-text en asunto (opcional, para búsqueda avanzada)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_email_send_subject_trgm
    ON email_send USING gin (subject gin_trgm_ops);

-- ============================================================
-- Tablas de Billing (LemonSqueezy)
-- ============================================================

-- Suscripciones de usuarios
CREATE TABLE IF NOT EXISTS subscriptions (
    id                      SERIAL PRIMARY KEY,
    tenant_id               INTEGER NOT NULL REFERENCES tenants(id),
    lemonqueezy_id          VARCHAR(255) UNIQUE,
    lemonqueezy_customer_id VARCHAR(255),
    plan_name               VARCHAR(50) NOT NULL DEFAULT 'free',
    plan_price              DECIMAL(10,2) DEFAULT 0,
    status                  VARCHAR(50) DEFAULT 'active',
    billing_cycle           VARCHAR(20) DEFAULT 'monthly',
    current_period_start    TIMESTAMP,
    current_period_end      TIMESTAMP,
    cancel_at               TIMESTAMP,
    created_at              TIMESTAMP DEFAULT NOW(),
    updated_at              TIMESTAMP DEFAULT NOW()
);

-- Facturas
CREATE TABLE IF NOT EXISTS invoices (
    id                      SERIAL PRIMARY KEY,
    tenant_id               INTEGER NOT NULL REFERENCES tenants(id),
    lemonqueezy_order_id    VARCHAR(255) UNIQUE,
    amount                  DECIMAL(10,2) NOT NULL,
    currency                VARCHAR(3) DEFAULT 'USD',
    status                  VARCHAR(50),
    invoice_url             TEXT,
    created_at              TIMESTAMP DEFAULT NOW()
);

-- Índices para billing
CREATE INDEX IF NOT EXISTS idx_subscriptions_tenant
    ON subscriptions (tenant_id);

CREATE INDEX IF NOT EXISTS idx_subscriptions_status
    ON subscriptions (status);

CREATE INDEX IF NOT EXISTS idx_invoices_tenant
    ON invoices (tenant_id, created_at DESC);

-- ============================================================
-- Datos de prueba (comentar en producción)
-- ============================================================

INSERT INTO email_send (message_id, email_to, email_from, subject, content, mime_type, status, created_at)
VALUES
  ('msg-001', 'juan@empresa.com', 'noreply@tudominio.com', 'Bienvenido a nuestra plataforma', '<h1>Hola Juan!</h1><p>Tu cuenta ha sido creada exitosamente.</p>', 'text/html', 'delivered', NOW() - INTERVAL '2 hours'),
  ('msg-002', 'maria@cliente.com', 'noreply@tudominio.com', 'Tu factura #1234 está lista', '<h1>Factura lista</h1><p>Puedes descargarla desde tu portal.</p>', 'text/html', 'delivered', NOW() - INTERVAL '5 hours'),
  ('msg-003', 'pedro@invalido.xxx', 'noreply@tudominio.com', 'Recordatorio de pago', 'Tu pago vence mañana.', 'text/plain', 'bounce', NOW() - INTERVAL '1 day'),
  ('msg-004', 'ana@spam.com', 'noreply@tudominio.com', 'Oferta especial', '<p>Aprovecha nuestra oferta.</p>', 'text/html', 'complaint', NOW() - INTERVAL '2 days'),
  ('msg-005', 'luis@empresa.com', 'noreply@tudominio.com', 'Tu reporte mensual', '<h1>Reporte de Marzo</h1><p>Adjuntamos el resumen.</p>', 'text/html', 'sent', NOW() - INTERVAL '10 minutes')
ON CONFLICT DO NOTHING;

INSERT INTO email_events (email_send_id, event_type, event_data, created_at)
VALUES
  (1, 'send',     '{"timestamp": "2024-03-01T10:00:00Z"}', NOW() - INTERVAL '2 hours'),
  (1, 'delivery', '{"timestamp": "2024-03-01T10:00:05Z", "smtpResponse": "250 OK"}', NOW() - INTERVAL '2 hours' + INTERVAL '5 seconds'),
  (2, 'send',     '{"timestamp": "2024-03-01T07:00:00Z"}', NOW() - INTERVAL '5 hours'),
  (2, 'delivery', '{"timestamp": "2024-03-01T07:00:03Z"}', NOW() - INTERVAL '5 hours' + INTERVAL '3 seconds'),
  (3, 'send',     '{"timestamp": "2024-02-29T12:00:00Z"}', NOW() - INTERVAL '1 day'),
  (3, 'bounce',   '{"bounceType": "Permanent", "bounceSubType": "NoEmail", "bouncedRecipients": [{"emailAddress": "pedro@invalido.xxx"}]}', NOW() - INTERVAL '1 day' + INTERVAL '10 seconds'),
  (4, 'send',     '{"timestamp": "2024-02-28T09:00:00Z"}', NOW() - INTERVAL '2 days'),
  (4, 'complaint','{"complaintFeedbackType": "abuse", "complainedRecipients": [{"emailAddress": "ana@spam.com"}]}', NOW() - INTERVAL '2 days' + INTERVAL '1 hour'),
  (5, 'send',     '{"timestamp": "2024-03-01T11:50:00Z"}', NOW() - INTERVAL '10 minutes')
ON CONFLICT DO NOTHING;