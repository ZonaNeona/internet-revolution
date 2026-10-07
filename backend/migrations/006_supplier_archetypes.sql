ALTER TABLE supplier_search_calls
    ADD COLUMN IF NOT EXISTS archetype_id BIGINT
        REFERENCES product_archetypes(id) ON DELETE CASCADE;

ALTER TABLE supplier_offers
    ADD COLUMN IF NOT EXISTS archetype_id BIGINT
        REFERENCES product_archetypes(id) ON DELETE CASCADE;

ALTER TABLE supplier_offers
    DROP CONSTRAINT IF EXISTS supplier_offers_run_id_source_source_url_key;

CREATE INDEX IF NOT EXISTS idx_supplier_search_calls_archetype
    ON supplier_search_calls (run_id, archetype_id, source, id);

CREATE INDEX IF NOT EXISTS idx_supplier_offers_archetype
    ON supplier_offers (run_id, archetype_id, source, id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_supplier_offers_run_arch_source_url
    ON supplier_offers (run_id, archetype_id, source, source_url)
    WHERE archetype_id IS NOT NULL;