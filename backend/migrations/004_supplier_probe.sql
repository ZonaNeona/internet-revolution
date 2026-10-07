ALTER TABLE research_runs
    ADD COLUMN IF NOT EXISTS supplier_actual_cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS supplier_search_calls INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS supplier_records INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS supplier_search_calls (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    query TEXT NOT NULL,
    engine TEXT NOT NULL DEFAULT 'exa',
    model TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running','done','failed','budget_blocked')),
    cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    result_count INTEGER NOT NULL DEFAULT 0,
    response_meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_supplier_search_calls_run
    ON supplier_search_calls (run_id, id);

CREATE TABLE IF NOT EXISTS supplier_offers (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    search_call_id BIGINT REFERENCES supplier_search_calls(id) ON DELETE SET NULL,
    source TEXT NOT NULL,
    supplier_name TEXT,
    product_title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    price_text TEXT,
    moq_text TEXT,
    lead_time_text TEXT,
    customization_text TEXT,
    feature_summary TEXT,
    country TEXT,
    source_quality NUMERIC(4,3) NOT NULL DEFAULT 0.80,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, source, source_url)
);

CREATE INDEX IF NOT EXISTS idx_supplier_offers_run_source
    ON supplier_offers (run_id, source, id);