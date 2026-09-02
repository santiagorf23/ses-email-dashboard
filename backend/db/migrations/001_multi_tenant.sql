-- ============================================================
-- Multi-Tenant Migration
-- ============================================================

-- Tabla de tenants
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    aws_access_key_enc TEXT,
    aws_secret_key_enc TEXT,
    aws_region TEXT DEFAULT 'us-east-1',
    aws_sns_topic_arn TEXT,
    plan TEXT DEFAULT 'free' CHECK (plan IN ('free', 'pro', 'business', 'enterprise')),
    plan_limits JSONB DEFAULT '{"max_emails": 1000, "max_domains": 1, "retention_days": 7}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabla de usuarios
CREATE TABLE IF NOT EXISTS app_users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'admin' CHECK (role IN ('admin', 'viewer', 'analyst')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON app_users(tenant_id);
CREATE INDEX idx_users_email ON app_users(email);

-- Agregar tenant_id a tablas existentes
ALTER TABLE email_send ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE email_events ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;
ALTER TABLE email_block ADD COLUMN IF NOT EXISTS tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE;

-- Índices para multi-tenant
CREATE INDEX IF NOT EXISTS idx_email_send_tenant ON email_send(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_events_tenant ON email_events(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_block_tenant ON email_block(tenant_id);

-- RLS (Row Level Security)
ALTER TABLE email_send ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_block ENABLE ROW LEVEL SECURITY;

-- Políticas de aislamiento por tenant
CREATE POLICY tenant_isolation_send ON email_send
    USING (tenant_id = current_setting('app.current_tenant')::int);

CREATE POLICY tenant_isolation_events ON email_events
    USING (tenant_id = current_setting('app.current_tenant')::int);

CREATE POLICY tenant_isolation_block ON email_block
    USING (tenant_id = current_setting('app.current_tenant')::int);

-- Tenant default para migración de datos existentes
INSERT INTO tenants (name, slug, plan, plan_limits)
VALUES ('Default', 'default', 'free', '{"max_emails": 10000, "max_domains": 1, "retention_days": 90}')
ON CONFLICT (slug) DO NOTHING;

-- Asignar datos existentes al tenant default
UPDATE email_send SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default') WHERE tenant_id IS NULL;
UPDATE email_events SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default') WHERE tenant_id IS NULL;
UPDATE email_block SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default') WHERE tenant_id IS NULL;

-- Hacer tenant_id NOT NULL después de migrar datos
ALTER TABLE email_send ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE email_events ALTER COLUMN tenant_id SET NOT NULL;
ALTER TABLE email_block ALTER COLUMN tenant_id SET NOT NULL;
