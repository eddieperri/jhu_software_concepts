-- schema.sql
-- Run this script to generate the necessary table for thegradcafe database

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