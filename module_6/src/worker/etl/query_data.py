# pylint: disable=duplicate-code
"""
Module for querying analytical metrics from the Grad Cafe PostgreSQL database.
Enforces safe SQL composition, inherent row limits, and least-privilege connectivity.
"""
import os
import psycopg
from psycopg import sql
from dotenv import load_dotenv

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

def safe_execute(cursor, query_string, limit_val=100):
    """
    Utility function to securely clamp limits and execute composed SQL.
    Clamps requested limit between 1 and 100.
    """
    clamped_limit = max(1, min(int(limit_val), 100))
    composed_query = sql.SQL(query_string + " LIMIT {limit};").format(
        limit=sql.Literal(clamped_limit)
    )
    cursor.execute(composed_query)
    return cursor

def get_demographic_metrics(cursor, metrics):
    """Retrieves basic volume and demographic metrics."""
    # Q1: Applied for Fall 2026
    safe_execute(cursor, "SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2026'", 1)
    metrics['q1'] = cursor.fetchone()[0]

    # Q2: Percentage of International Students
    safe_execute(cursor, """
        SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE us_or_international = 'International') 
        / NULLIF(COUNT(*), 0), 2) FROM applicants
    """, 1)
    metrics['q2'] = cursor.fetchone()[0] or 0.00

def get_academic_metrics(cursor, metrics):
    """Retrieves GPA and GRE statistical metrics."""
    # Q3: Average GPA, GRE
    safe_execute(cursor, """
        SELECT ROUND(AVG(gpa)::numeric, 2), ROUND(AVG(gre)::numeric, 1), 
               ROUND(AVG(gre_v)::numeric, 1), ROUND(AVG(gre_aw)::numeric, 1)
        FROM applicants 
        WHERE (gpa IS NOT NULL AND gpa <= 4.0) AND (gre BETWEEN 130 AND 170)
        AND (gre_v BETWEEN 130 AND 170) AND (gre_aw BETWEEN 0 AND 6.0)
    """, 1)
    res = cursor.fetchone()
    metrics['q3_gpa'] = res[0] if res[0] is not None else 0
    metrics['q3_gre'] = res[1] if res[1] is not None else 0
    metrics['q3_grev'] = res[2] if res[2] is not None else 0
    metrics['q3_greaw'] = res[3] if res[3] is not None else 0

    # Q4 & Q6: GPA of American Students and Acceptances
    safe_execute(cursor, """
        SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants 
        WHERE term = 'Fall 2026' AND us_or_international = 'American'
    """, 1)
    metrics['q4'] = cursor.fetchone()[0] or 0

    safe_execute(cursor, """
        SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants 
        WHERE term = 'Fall 2026' AND status ILIKE 'Accepted%'
    """, 1)
    metrics['q6'] = cursor.fetchone()[0] or 0

def get_program_metrics(cursor, metrics):
    """Retrieves program-specific acceptance metrics and trends."""
    # Q5: Percent Acceptance Fall 2026
    safe_execute(cursor, """
        SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status ILIKE 'Accepted%') 
        / NULLIF(COUNT(*), 0), 2) FROM applicants WHERE term = 'Fall 2026'
    """, 1)
    metrics['q5'] = cursor.fetchone()[0] or 0.00

    # Q7, Q8, Q9: Specific Program Volumes
    safe_execute(cursor, """
        SELECT COUNT(*) FROM applicants WHERE llm_generated_university = 'Johns Hopkins University' 
        AND degree = 'Masters' AND llm_generated_program ILIKE '%Computer Science%'
    """, 1)
    metrics['q7'] = cursor.fetchone()[0]

    safe_execute(cursor, """
        SELECT COUNT(*) FROM applicants 
        WHERE term ILIKE '%2026%' AND status ILIKE 'Accepted%' AND degree = 'PhD'
        AND llm_generated_university IN ('Georgetown University', 'Massachusetts Institute of Technology', 
        'Stanford University', 'Carnegie Mellon University')
        AND llm_generated_program ILIKE '%Computer Science%'
    """, 1)
    metrics['q8'] = cursor.fetchone()[0]

    safe_execute(cursor, """
        SELECT COUNT(*) FROM applicants 
        WHERE term ILIKE '%2026%' AND status ILIKE 'Accepted%' AND degree = 'PhD'
        AND program ILIKE '%Computer Science%' AND (program ILIKE '%Georgetown%' 
        OR program ILIKE '%Massachusetts Institute of Technology%' OR program ILIKE '%MIT%' 
        OR program ILIKE '%Stanford%' OR program ILIKE '%Carnegie Mellon%')
    """, 1)
    metrics['q9_raw'] = cursor.fetchone()[0]

    # Q10 & Q11: Top Programs and Monthly Trends (Notice the limits here)
    safe_execute(cursor, """
        SELECT llm_generated_program, COUNT(*) as volume FROM applicants
        GROUP BY llm_generated_program ORDER BY volume DESC
    """, 5)
    metrics['q10'] = cursor.fetchall()

    safe_execute(cursor, """
        SELECT TO_CHAR(date_added, 'Month') as month_name, COUNT(*) as count 
        FROM applicants WHERE date_added IS NOT NULL GROUP BY month_name ORDER BY count DESC
    """, 12)
    metrics['q11'] = cursor.fetchall()

def get_metrics():
    """
    Coordinates the execution of analytical SQL queries and returns a metrics dictionary.
    Uses cached analytics if available for faster UI reads.
    """
    metrics = {}
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("SELECT payload FROM analytics_cache WHERE name = 'default'")
                    row = cur.fetchone()
                except psycopg.errors.UndefinedTable:
                    row = None

                if row is not None:
                    raw_payload = row[0]
                    if isinstance(raw_payload, dict):
                        metrics = raw_payload
                    else:
                        import json as _json
                        metrics = _json.loads(raw_payload)
                else:
                    get_demographic_metrics(cur, metrics)
                    get_academic_metrics(cur, metrics)
                    get_program_metrics(cur, metrics)
    except psycopg.Error as e:
        print(f"Database error occurred: {e}")
        raise e

    return metrics

if __name__ == "__main__": # pragma: no cover
    print(get_metrics())
