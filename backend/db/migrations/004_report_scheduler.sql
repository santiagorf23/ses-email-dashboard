-- ============================================================
-- Report Scheduler
-- ============================================================

CREATE TABLE IF NOT EXISTS report_config (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    
    report_type TEXT DEFAULT 'weekly' CHECK (report_type IN ('weekly', 'monthly')),
    frequency_hours INTEGER DEFAULT 168,  -- 7 days
    is_enabled BOOLEAN DEFAULT FALSE,
    last_sent_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tenant_id)
);

-- Default config for default tenant
INSERT INTO report_config (tenant_id)
SELECT id FROM tenants WHERE slug = 'default'
ON CONFLICT (tenant_id) DO NOTHING;
