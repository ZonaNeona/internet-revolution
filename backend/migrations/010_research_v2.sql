ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS analysis_mode TEXT NOT NULL DEFAULT 'category'
    CHECK (analysis_mode IN ('category','product'));
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS selected_markets JSONB NOT NULL DEFAULT '["wb","ozon","amazon","lazada"]';
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS pipeline_version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS quality TEXT NOT NULL DEFAULT 'pending';
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS warnings JSONB NOT NULL DEFAULT '[]';
CREATE TABLE IF NOT EXISTS budget_calls (
    id BIGSERIAL PRIMARY KEY, run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    kind TEXT NOT NULL, reserved NUMERIC(12,6) NOT NULL, cost NUMERIC(12,6),
    state TEXT NOT NULL DEFAULT 'reserved', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS budget_calls_day ON budget_calls(created_at);
CREATE TABLE IF NOT EXISTS marketplace_economics (
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    archetype_id BIGINT NOT NULL REFERENCES product_archetypes(id) ON DELETE CASCADE,
    market TEXT NOT NULL, payload JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(run_id,archetype_id,market)
);
CREATE TABLE IF NOT EXISTS worker_health (
    id INTEGER PRIMARY KEY, heartbeat TIMESTAMPTZ NOT NULL DEFAULT now()
);
