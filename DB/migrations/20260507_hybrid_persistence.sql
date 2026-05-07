CREATE TABLE IF NOT EXISTS metrics_events (
    metric_id BIGSERIAL PRIMARY KEY,
    company_id TEXT,
    session_id TEXT,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_metrics_events_company_created
ON metrics_events (company_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_metrics_events_session
ON metrics_events (session_id);

CREATE INDEX IF NOT EXISTS idx_metrics_events_event_type
ON metrics_events (event_type);


CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    full_name TEXT,
    email TEXT NOT NULL,
    cpf TEXT,
    phone TEXT,
    age INTEGER,
    gender TEXT,
    favorite_brands JSONB NOT NULL DEFAULT '[]'::jsonb,
    lgpd_consent BOOLEAN NOT NULL DEFAULT FALSE,
    newsletter_opt_in BOOLEAN NOT NULL DEFAULT TRUE,
    consent_version TEXT,
    source TEXT,
    ip_address TEXT,
    user_agent TEXT,
    access_page_url TEXT,
    recovery_page_url TEXT,
    access_qr_url TEXT,
    recovery_qr_url TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_company_email
ON leads (company_id, email);

CREATE INDEX IF NOT EXISTS idx_leads_company_session
ON leads (company_id, session_id);

CREATE INDEX IF NOT EXISTS idx_leads_company_created
ON leads (company_id, created_at DESC);


CREATE TABLE IF NOT EXISTS consents (
    consent_id TEXT PRIMARY KEY,
    company_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    lead_id TEXT,
    email TEXT NOT NULL,
    full_name TEXT,
    lgpd_consent BOOLEAN NOT NULL DEFAULT FALSE,
    newsletter_opt_in BOOLEAN NOT NULL DEFAULT TRUE,
    consent_version TEXT,
    consent_text TEXT,
    source TEXT,
    ip_address TEXT,
    user_agent TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consents_company_email
ON consents (company_id, email);

CREATE INDEX IF NOT EXISTS idx_consents_lead
ON consents (lead_id);

CREATE INDEX IF NOT EXISTS idx_consents_company_created
ON consents (company_id, created_at DESC);


CREATE TABLE IF NOT EXISTS sync_audit (
    sync_id TEXT PRIMARY KEY,
    entity TEXT NOT NULL,
    operation TEXT NOT NULL,
    company_id TEXT,
    session_id TEXT,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    synced_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sync_audit_company_status
ON sync_audit (company_id, status);

CREATE INDEX IF NOT EXISTS idx_sync_audit_entity_status
ON sync_audit (entity, status);

CREATE INDEX IF NOT EXISTS idx_sync_audit_created
ON sync_audit (created_at DESC);
