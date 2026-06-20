import json
import psycopg
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def get_db_connection():
    """
    Establishes and returns a connection to the PostgreSQL database.

    Retrieves the database connection string from the 'DATABASE_URL'
    environment variable. Defaults to a local test configuration if not found.

    :returns: An active PostgreSQL connection instance.
    :rtype: psycopg.Connection
    """
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/thegradcafe')
    return psycopg.connect(conninfo=db_url)

def clean_numeric(val, min_val, max_val):
    """
    Sanitizes and validates numeric data scraped from the web.

    Attempts to convert a raw string or numeric input into a float.
    Enforces logical minimum and maximum boundaries to filter out
    user-entry errors and scraping artifacts.

    :param val: The raw input value to be sanitized (e.g., from a JSON field).
    :type val: str, float, or None
    :param min_val: The absolute minimum acceptable limit for the value.
    :type min_val: float
    :param max_val: The absolute maximum acceptable limit for the value.
    :type max_val: float
    :returns: The sanitized float if within bounds, or None if invalid/out-of-bounds.
    :rtype: float or None
    """
    try:
        if val is None or val == "":
            return None
        # Clean up any potential extra spaces
        f_val = float(str(val).strip())
        if min_val <= f_val <= max_val:
            return f_val
        return None # Out of bounds (e.g., GPA > 4.0)
    except (ValueError, TypeError):
        return None # Not a number

def load_data(json_path='src/web_scraping/applicant_data.json'):
    """
    Loads the standardized applicant JSON dataset into PostgreSQL.

    This function handles the extraction of JSON data, connects to the 
    database, and executes the table creation (if missing). It sanitizes 
    all fields using boundary constraints and handles date formatting. 
    Idempotency is guaranteed via an 'ON CONFLICT DO NOTHING' unique 
    constraint applied to the applicant's result URL.

    :param json_path: The file path to the target JSON data. Defaults to the main scraped dataset.
    :type json_path: str
    :raises FileNotFoundError: If the specified JSON data file does not exist.
    :raises Exception: If a database transaction fails or schema constraints are violated.
    """
    print(f"Loading JSON data from {json_path}...")
    
    # Check if file exists (crucial for passing tests that simulate missing files)
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Data file not found at {json_path}")
        
    with open(json_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    print(f"Found {len(data)} records. Connecting to database...")
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. Ensure the table and uniqueness constraint exist.
                # We use 'url' as the unique identifier to prevent duplicate rows
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS applicants (
                        p_id SERIAL PRIMARY KEY,
                        program TEXT NOT NULL,
                        comments TEXT,
                        date_added DATE,
                        url TEXT UNIQUE NOT NULL,
                        status TEXT NOT NULL,
                        term TEXT NOT NULL,
                        us_or_international TEXT,
                        gpa NUMERIC,
                        gre NUMERIC,
                        gre_v NUMERIC,
                        gre_aw NUMERIC,
                        degree TEXT,
                        llm_generated_program TEXT,
                        llm_generated_university TEXT
                    );
                """)
                
                # 2. Insert rows, respecting the uniqueness policy
                for row in data:
                    # Clean data using our helper
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
                    
                    # The URL is required for our uniqueness constraint. 
                    # If it's missing, we skip the row to avoid database errors.
                    url = row.get("result url")
                    if not url:
                        continue

                    # Execute Insert with Idempotency constraint (ON CONFLICT DO NOTHING)
                    cur.execute("""
                        INSERT INTO applicants (
                            program, comments, date_added, url, status, term,
                            us_or_international, gpa, gre, gre_v, gre_aw, degree,
                            llm_generated_program, llm_generated_university
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (url) DO NOTHING;
                    """, (
                        row.get("program", "Unknown Program"), # Ensure required fields are met
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

    except Exception as e:
        print(f"An error occurred: {e}")
        # Re-raise the exception so Pytest can catch it during error-path testing
        raise e 

if __name__ == "__main__":
    load_data()