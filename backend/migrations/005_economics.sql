CREATE TABLE IF NOT EXISTS economics_scenarios (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    archetype_id BIGINT NOT NULL REFERENCES product_archetypes(id) ON DELETE CASCADE,
    status TEXT NOT NULL
        CHECK (status IN ('ready','partial','insufficient_data')),
    currency TEXT NOT NULL DEFAULT 'RUB',
    retail_price_min NUMERIC(14,2),
    retail_price_max NUMERIC(14,2),
    retail_evidence_count INTEGER NOT NULL DEFAULT 0,
    supplier_price_min_usd NUMERIC(14,4),
    supplier_price_max_usd NUMERIC(14,4),
    supplier_evidence_count INTEGER NOT NULL DEFAULT 0,
    landed_cost_min_rub NUMERIC(14,2),
    landed_cost_max_rub NUMERIC(14,2),
    contribution_margin_min NUMERIC(7,2),
    contribution_margin_max NUMERIC(7,2),
    assumptions JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    notes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, archetype_id)
);

CREATE INDEX IF NOT EXISTS idx_economics_scenarios_run
    ON economics_scenarios (run_id, status, id);