CREATE TABLE IF NOT EXISTS workstation_status_events (
    id BIGSERIAL PRIMARY KEY,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    reported_at TIMESTAMPTZ NULL,
    computer_name TEXT NOT NULL,
    reported_user TEXT NULL,
    sam_account_name TEXT NULL,
    ip_address INET NULL,
    source TEXT NOT NULL DEFAULT 'gpo_scheduled_task',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_workstation_status_events_user_received
    ON workstation_status_events (lower(sam_account_name), received_at DESC)
    WHERE sam_account_name IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_workstation_status_events_computer_received
    ON workstation_status_events (lower(computer_name), received_at DESC);
