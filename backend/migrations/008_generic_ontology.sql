ALTER TABLE research_runs
    ADD COLUMN IF NOT EXISTS research_mode TEXT NOT NULL DEFAULT 'preset',
    ADD COLUMN IF NOT EXISTS ontology_status TEXT,
    ADD COLUMN IF NOT EXISTS ontology JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS ontology_cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_research_runs_query_mode
    ON research_runs (research_mode, created_at DESC);
