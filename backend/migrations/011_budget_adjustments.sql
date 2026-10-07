CREATE TABLE IF NOT EXISTS budget_adjustments (
    source TEXT NOT NULL, day DATE NOT NULL, cost NUMERIC(12,6) NOT NULL,
    PRIMARY KEY(source,day)
);
