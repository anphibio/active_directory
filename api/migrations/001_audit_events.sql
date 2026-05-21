CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    event TEXT NOT NULL,
    operator TEXT NULL,
    target TEXT NULL,
    correlation_id TEXT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_audit_events_occurred_at ON audit_events (occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_event ON audit_events (event);
CREATE INDEX IF NOT EXISTS idx_audit_events_operator ON audit_events (operator);
CREATE INDEX IF NOT EXISTS idx_audit_events_target ON audit_events (target);
