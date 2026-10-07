CREATE TABLE IF NOT EXISTS structured_response_cache (
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    input_sha TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id,kind,input_sha)
);
