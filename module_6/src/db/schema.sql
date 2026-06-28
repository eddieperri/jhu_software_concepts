-- Run this script to generate the necessary tables for thegradcafe database

DROP TABLE IF EXISTS applicants;

CREATE TABLE applicants (
    p_id SERIAL PRIMARY KEY,
    program VARCHAR(255),
    comments TEXT,
    date_added DATE,
    url VARCHAR(255) UNIQUE,
    status VARCHAR(100),
    term VARCHAR(100),
    us_or_international VARCHAR(50),
    gpa NUMERIC(4,2),
    gre NUMERIC(5,1),
    gre_v NUMERIC(5,1),
    gre_aw NUMERIC(3,1),
    degree VARCHAR(50),
    llm_generated_program VARCHAR(255),
    llm_generated_university VARCHAR(255)
);

--  Watermark table for idempotent inserts
CREATE TABLE IF NOT EXISTS ingestion_watermarks (
    source TEXT PRIMARY KEY,
    last_seen TEXT,
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Initialize the watermark row
INSERT INTO ingestion_watermarks (source, last_seen) 
VALUES ('gradcafe_scraper', '') 
ON CONFLICT DO NOTHING;