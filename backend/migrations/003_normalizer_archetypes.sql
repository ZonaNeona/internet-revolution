CREATE TABLE IF NOT EXISTS normalized_products (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    raw_product_id BIGINT NOT NULL REFERENCES raw_products(id) ON DELETE CASCADE,
    market TEXT NOT NULL,
    canonical_title TEXT NOT NULL,
    canonical_brand TEXT,
    archetype_key TEXT NOT NULL,
    archetype_label TEXT NOT NULL,
    relevance_score NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    normalization_method TEXT NOT NULL DEFAULT 'rules_v1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, raw_product_id)
);

CREATE INDEX IF NOT EXISTS idx_normalized_products_run
    ON normalized_products (run_id, archetype_key, market);

CREATE TABLE IF NOT EXISTS product_archetypes (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    dataset_key TEXT NOT NULL,
    archetype_key TEXT NOT NULL,
    label TEXT NOT NULL,
    member_count INTEGER NOT NULL DEFAULT 0,
    market_count INTEGER NOT NULL DEFAULT 0,
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, archetype_key)
);

CREATE TABLE IF NOT EXISTS archetype_members (
    archetype_id BIGINT NOT NULL REFERENCES product_archetypes(id) ON DELETE CASCADE,
    normalized_product_id BIGINT NOT NULL REFERENCES normalized_products(id) ON DELETE CASCADE,
    membership_score NUMERIC(5,4) NOT NULL DEFAULT 1.0,
    PRIMARY KEY (archetype_id, normalized_product_id)
);

CREATE TABLE IF NOT EXISTS market_signals (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    archetype_id BIGINT NOT NULL REFERENCES product_archetypes(id) ON DELETE CASCADE,
    market TEXT NOT NULL,
    offer_count INTEGER NOT NULL DEFAULT 0,
    presence_score NUMERIC(6,2) NOT NULL DEFAULT 0,
    review_mass BIGINT NOT NULL DEFAULT 0,
    avg_rating NUMERIC(5,2),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, archetype_id, market)
);

CREATE TABLE IF NOT EXISTS opportunity_scores (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    archetype_id BIGINT NOT NULL REFERENCES product_archetypes(id) ON DELETE CASCADE,
    foreign_signal NUMERIC(6,2) NOT NULL DEFAULT 0,
    russia_signal NUMERIC(6,2) NOT NULL DEFAULT 0,
    cross_market_presence NUMERIC(6,2) NOT NULL DEFAULT 0,
    russia_gap NUMERIC(6,2) NOT NULL DEFAULT 0,
    review_mass_score NUMERIC(6,2) NOT NULL DEFAULT 0,
    feature_recurrence NUMERIC(6,2) NOT NULL DEFAULT 0,
    opportunity_score NUMERIC(6,2) NOT NULL DEFAULT 0,
    explanation JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, archetype_id)
);

CREATE INDEX IF NOT EXISTS idx_opportunity_scores_run
    ON opportunity_scores (run_id, opportunity_score DESC);