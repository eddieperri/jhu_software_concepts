import json
import psycopg
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

DB_PARAMS = {
    "dbname": "thegradcafe",
    "user": "postgres",
    "password": os.environ.get("DB_PASSWORD"), 
    "host": "localhost",
    "port": 5432
}

def clean_numeric(val, min_val, max_val):
    """Helper to safely convert strings to floats and enforce logical bounds."""
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

def load_data():
    print("Loading JSON data...")
    # Make sure this path matches your folder structure
    with open('web_scraping/applicant_data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    print(f"Found {len(data)} records. Connecting to database...")
    
    try:
        with psycopg.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                # Wipe the table to ensure clean state
                cur.execute("TRUNCATE TABLE applicants;")
                
                for index, row in enumerate(data, start=1):
                    # Clean data using our helper
                    gpa = clean_numeric(row.get("uGPA"), 0.0, 4.0)
                    gre_q = clean_numeric(row.get("GRE Quant"), 130, 170)
                    gre_v = clean_numeric(row.get("GRE Verbal"), 130, 170)
                    gre_aw = clean_numeric(row.get("GRE AW"), 0.0, 6.0)

                    raw_date = row.get("date added") # e.g., "Added on May 29, 2026"
                    clean_date = None
                    if raw_date:
                        try:
                            # Remove "Added on " to leave "May 29, 2026"
                            date_str = raw_date.replace("Added on ", "")
                            clean_date = datetime.strptime(date_str, "%b %d, %Y").date()
                        except ValueError:
                            clean_date = None # If parsing fails, store NULL
                    
                    is_intl = row.get("I/International") == "International"

                    # Execute Insert
                    cur.execute("""
                        INSERT INTO applicants (
                            p_id, program, comments, date_added, url, status, term,
                            us_or_international, gpa, gre, gre_v, gre_aw, degree,
                            llm_generated_program, llm_generated_university
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        index, 
                        row.get("program"), 
                        row.get("comments"), 
                        clean_date,
                        row.get("result url"), 
                        row.get("status"), 
                        row.get("term"),
                        row.get("I/International"), # Keeping as text to match rubric
                        gpa, 
                        gre_q, # This maps to the SQL 'gre' column
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

if __name__ == "__main__":
    load_data()