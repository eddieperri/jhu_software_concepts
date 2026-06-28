# pylint: disable=duplicate-code
"""
Module for sanitizing and loading applicant JSON datasets into PostgreSQL.
Enforces safe SQL composition and least-privilege database connectivity.
"""
import os
import json
from datetime import datetime

import psycopg
from psycopg import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """
    Establishes and returns a connection to the PostgreSQL database.
    Prioritizes an explicit DATABASE_URL (for testing/CI) before falling 
    back to local least-privilege environment variables.
    """
    # 1. Check if Pytest or GitHub Actions handed us a temporary test database
    test_db_url = os.environ.get("DATABASE_URL")
    if test_db_url:
        return psycopg.connect(conninfo=test_db_url)

    # 2. Otherwise, connect to the real local database
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "thegradcafe"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def clean_numeric(val, min_val, max_val):
    """
    Sanitizes and validates numeric data scraped from the web.
    Enforces minimum and maximum boundaries to filter out artifacts.
    """
    try:
        if val is None or val == "":
            return None
        f_val = float(str(val).strip())
        if min_val <= f_val <= max_val:
            return f_val
        return None
    except (ValueError, TypeError):
        return None

def process_single_row(row, cursor, insert_stmt):
    """
    Extracts, sanitizes, and safely inserts a single JSON row into the database.
    Abstracted to reduce local variable count in the main load loop.
    """
    url = row.get("result url")
    if not url:
        return

    gpa = clean_numeric(row.get("uGPA"), 0.0, 4.0)
    gre_q = clean_numeric(row.get("GRE Quant"), 130, 170)
    gre_v = clean_numeric(row.get("GRE Verbal"), 130, 170)
    gre_aw = clean_numeric(row.get("GRE AW"), 0.0, 6.0)

    raw_date = row.get("date added")
    clean_date = None
    if raw_date:
        try:
            date_str = raw_date.replace("Added on ", "")
            clean_date = datetime.strptime(date_str, "%b %d, %Y").date()
        except ValueError:
            clean_date = None

    cursor.execute(insert_stmt, (
        row.get("program", "Unknown Program"),
        row.get("comments"),
        clean_date,
        url,
        row.get("status", "Unknown Status"),
        row.get("term", "Unknown Term"),
        row.get("I/International"),
        gpa,
        gre_q,
        gre_v,
        gre_aw,
        row.get("Degree"),
        row.get("llm-generated-program"),
        row.get("llm-generated-university")
    ))

def load_data(json_path=None):
    """
    Loads the standardized applicant JSON dataset into PostgreSQL.
    Uses safe psycopg composition and handles relative/absolute paths.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))

    if json_path is None:
        # FIX 1: Point to the new data directory
        json_path = os.path.join(base_dir, "..", "data", "applicant_data.json")

    print(f"Loading JSON data from {json_path}...")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Data file not found at {json_path}")

    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    print(f"Found {len(data)} records. Connecting to database...")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:

                # FIX 2: Execute the schema.sql file to create the tables first
                schema_path = os.path.join(base_dir, "schema.sql")
                if os.path.exists(schema_path):
                    with open(schema_path, 'r', encoding='utf-8') as schema_file:
                        cur.execute(schema_file.read())
                        print("Schema executed successfully.")

                # Create the watermark table requested by the rubric
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS ingestion_watermarks (
                        source TEXT PRIMARY KEY,
                        last_seen TEXT,
                        updated_at TIMESTAMPTZ DEFAULT now()
                    );
                """)
                cur.execute("""
                    INSERT INTO ingestion_watermarks (source, last_seen) 
                    VALUES ('gradcafe_scraper', '') 
                    ON CONFLICT DO NOTHING;
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS analytics_cache (
                        name TEXT PRIMARY KEY,
                        payload JSONB NOT NULL,
                        updated_at TIMESTAMPTZ DEFAULT now()
                    );
                """)

                # Build secure composition topology for data ingestion
                insert_query = sql.SQL("""
                    INSERT INTO {table} (
                        program, comments, date_added, url, status, term,
                        us_or_international, gpa, gre, gre_v, gre_aw, degree,
                        llm_generated_program, llm_generated_university
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING;
                """).format(table=sql.Identifier('applicants'))

                # Execute bounded insertion
                for row in data:
                    process_single_row(row, cur, insert_query)

                conn.commit()
                print("Migration complete! Data sanitized and loaded.")

    except psycopg.Error as e:
        print(f"A database error occurred: {e}")
        raise e

if __name__ == "__main__": # pragma: no cover
    load_data()
