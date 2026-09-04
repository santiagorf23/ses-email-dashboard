-- A/B Testing tables
-- Migration 003: A/B Testing

CREATE TABLE IF NOT EXISTS ab_tests (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    subject_a VARCHAR(500) NOT NULL,
    subject_b VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'running', 'completed')),
    winner VARCHAR(1) CHECK (winner IN ('a', 'b')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for tenant queries
CREATE INDEX IF NOT EXISTS idx_ab_tests_tenant_id ON ab_tests(tenant_id);
CREATE INDEX IF NOT EXISTS idx_ab_tests_status ON ab_tests(status);

-- Enable RLS
ALTER TABLE ab_tests ENABLE ROW LEVEL SECURITY;

-- RLS policies
CREATE POLICY ab_tests_tenant_isolation ON ab_tests
    USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);

-- Heatmap data table
CREATE TABLE IF NOT EXISTS email_engagement (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email_send_id INTEGER NOT NULL REFERENCES email_send(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_hour INTEGER NOT NULL CHECK (event_hour >= 0 AND event_hour <= 23),
    event_day INTEGER NOT NULL CHECK (event_day >= 0 AND event_day <= 6),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for heatmap queries
CREATE INDEX IF NOT EXISTS idx_email_engagement_tenant_id ON email_engagement(tenant_id);
CREATE INDEX IF NOT EXISTS idx_email_engagement_hour_day ON email_engagement(event_hour, event_day);
CREATE INDEX IF NOT EXISTS idx_email_engagement_event_type ON email_engagement(event_type);

-- Enable RLS
ALTER TABLE email_engagement ENABLE ROW LEVEL SECURITY;

-- RLS policies
CREATE POLICY email_engagement_tenant_isolation ON email_engagement
    USING (tenant_id = current_setting('app.current_tenant_id')::INTEGER);
