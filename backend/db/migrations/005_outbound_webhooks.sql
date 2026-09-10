-- ============================================================
-- Outbound Webhooks
-- ============================================================

CREATE TABLE IF NOT EXISTS webhook_config (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    url TEXT NOT NULL,
    secret TEXT,
    events TEXT[] DEFAULT ARRAY['alert.created', 'report.generated'],
    is_enabled BOOLEAN DEFAULT TRUE,
    
    last_triggered_at TIMESTAMPTZ,
    last_status_code INTEGER,
    fail_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id, url)
);

CREATE INDEX idx_webhook_config_tenant ON webhook_config(tenant_id);

-- Outbound webhook log
CREATE TABLE IF NOT EXISTS webhook_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    webhook_config_id INTEGER REFERENCES webhook_config(id) ON DELETE SET NULL,
    
    event_type TEXT NOT NULL,
    url TEXT NOT NULL,
    status_code INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webhook_logs_tenant ON webhook_logs(tenant_id, created_at DESC);
