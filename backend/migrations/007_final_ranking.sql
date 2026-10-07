ALTER TABLE opportunity_scores
    ADD COLUMN IF NOT EXISTS market_score NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS supplier_availability_score NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS economics_score NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS final_score NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS decision TEXT,
    ADD COLUMN IF NOT EXISTS final_explanation JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE opportunity_scores
SET market_score = COALESCE(market_score, opportunity_score),
    final_score = COALESCE(final_score, opportunity_score)
WHERE market_score IS NULL OR final_score IS NULL;

CREATE INDEX IF NOT EXISTS idx_opportunity_scores_final
    ON opportunity_scores (run_id, final_score DESC);