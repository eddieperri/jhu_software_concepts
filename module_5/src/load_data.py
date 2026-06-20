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
    Uses least-privilege credentials loaded via environment variables.
    """
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

def load_data(json_path=None):
    """
    Loads the standardized applicant JSON dataset into PostgreSQL.
    Uses safe psycopg composition and handles relative/absolute paths.
    """
    # Dynamically resolve absolute path to avoid subprocess FileNotFoundError
    if json_path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "web_scraping", "applicant_data.json")

    print(f"Loading JSON data from {json_path}...")

    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Data file not found at {json_path}")

    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    print(f"Found {len(data)} records. Connecting to database...")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 2. Build secure composition topology for data ingestion
                insert_query = sql.SQL("""
                    INSERT INTO {table} (
                        program, comments, date_added, url, status, term,
                        us_or_international, gpa, gre, gre_v, gre_aw, degree,
                        llm_generated_program, llm_generated_university
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING;
                """).format(table=sql.Identifier('applicants'))

                # 3. Execute bounded insertion
                for row in data:
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

                    url = row.get("result url")
                    if not url:
                        continue

                    cur.execute(insert_query, (
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

                conn.commit()
                print("Migration complete! Data sanitized and loaded.")

    except psycopg.Error as e:
        print(f"A database error occurred: {e}")
        raise e

if __name__ == "__main__":
    load_data()
