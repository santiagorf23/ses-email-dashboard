-- ============================================================
-- Alertas de Deliverability
-- ============================================================

-- Tabla de configuración de alertas por tenant
CREATE TABLE IF NOT EXISTS alert_config (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    -- Umbrales de bounce
    bounce_rate_threshold NUMERIC(5,2) DEFAULT 5.0,
    bounce_rate_window_hours INTEGER DEFAULT 24,
    sudden_bounce_count INTEGER DEFAULT 10,
    sudden_bounce_window_minutes INTEGER DEFAULT 60,
    
    -- Umbrales de complaint
    complaint_rate_threshold NUMERIC(5,2) DEFAULT 0.1,
    complaint_rate_window_hours INTEGER DEFAULT 24,
    
    -- Umbrales de blocked
    blocked_count_threshold INTEGER DEFAULT 5,
    blocked_window_hours INTEGER DEFAULT 24,
    
    -- Configuración de notificaciones
    notify_email TEXT,
    notify_slack_webhook TEXT,
    is_enabled BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id)
);

-- Tabla de alertas generadas
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    alert_type TEXT NOT NULL CHECK (alert_type IN ('bounce_rate', 'complaint_rate', 'sudden_bounce', 'blocked_count')),
    severity TEXT NOT NULL CHECK (severity IN ('warning', 'critical')),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    current_value NUMERIC(10,2),
    threshold_value NUMERIC(10,2),
    is_read BOOLEAN DEFAULT FALSE,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_alerts_tenant ON alerts(tenant_id, created_at DESC);
CREATE INDEX idx_alerts_unread ON alerts(tenant_id, is_read) WHERE is_read = FALSE;

-- Configuración por defecto para el tenant default
INSERT INTO alert_config (tenant_id, notify_email)
SELECT id, 'admin@default.com' FROM tenants WHERE slug = 'default'
ON CONFLICT (tenant_id) DO NOTHING;
