ALTER TABLE research_runs
    ADD COLUMN IF NOT EXISTS actual_cost_usd NUMERIC(10,6) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS live_search_calls INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS live_records INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS search_calls (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    market TEXT NOT NULL,
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

CREATE INDEX IF NOT EXISTS idx_search_calls_run
    ON search_calls (run_id, id);

CREATE INDEX IF NOT EXISTS idx_search_calls_day
    ON search_calls (created_at DESC);

CREATE TABLE IF NOT EXISTS raw_products (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    search_call_id BIGINT REFERENCES search_calls(id) ON DELETE SET NULL,
    market TEXT NOT NULL,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    brand TEXT,
    price_text TEXT,
    rating NUMERIC(4,2),
    review_count INTEGER,
    feature_summary TEXT,
    source_quality NUMERIC(4,3) NOT NULL DEFAULT 0.70,
    raw_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, market, source_url)
);

CREATE INDEX IF NOT EXISTS idx_raw_products_run_market
    ON raw_products (run_id, market, id);

CREATE TABLE IF NOT EXISTS source_documents (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    search_call_id BIGINT REFERENCES search_calls(id) ON DELETE SET NULL,
    market TEXT NOT NULL,
    source_url TEXT NOT NULL,
    title TEXT,
    source_kind TEXT NOT NULL DEFAULT 'search_result',
    meta JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, source_url)
);