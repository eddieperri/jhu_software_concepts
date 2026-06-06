import json
import psycopg
import os

# Grab the password from the environment (or default to a placeholder)
db_password = os.environ.get('DB_PASSWORD', 'default_password_if_missing')

DB_PARAMS = {
    "dbname": "thegradcafe",
    "user": "postgres",
    "password": db_password, 
    "host": "localhost",
    "port": 5432
}

def migrate_data():
    print("Loading JSON data...")
    # 2. Load the JSON data
    with open('web_scraping/applicant_data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)

    print(f"Found {len(data)} records. Connecting to database...")
    
    # 3. Connect to PostgreSQL using psycopg (v3)
    try:
        with psycopg.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                
                # 4. Iterate through JSON and insert into DB
                for index, row in enumerate(data, start=1):
                    
                    # --- DATA TRANSLATION & CLEANING ---
                    
                    # Convert "I/International" to a boolean
                    is_intl = row.get("I/International") == "International"
                    
                    # Safely convert GPA to float (handles missing or empty strings)
                    raw_gpa = row.get("uGPA")
                    gpa = float(raw_gpa) if raw_gpa else None
                    
                    # Safely convert GRE scores (assuming your full data might have these)
                    # If the keys don't exist in a record, they default to None (SQL NULL)
                    gre_q = float(row.get("GRE Q")) if row.get("GRE Q") else None
                    gre_v = float(row.get("GRE V")) if row.get("GRE V") else None
                    gre_aw = float(row.get("GRE AW")) if row.get("GRE AW") else None

                    # --- EXECUTE SQL INSERT ---
                    cur.execute("""
                        INSERT INTO applicants (
                            id, program, comments, date_added, url, status, term,
                            is_international, gpa, gre_q, gre_v, gre_aw, degree,
                            llm_generated_program, llm_generated_university
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        index, # Generates a unique ID starting at 1
                        row.get("program"), 
                        row.get("comments"), 
                        row.get("date added"),
                        row.get("result url"), 
                        row.get("status"), 
                        row.get("term"),
                        is_intl, 
                        gpa, 
                        gre_q, 
                        gre_v, 
                        gre_aw, 
                        row.get("Degree"),
                        row.get("llm-generated-program"), 
                        row.get("llm-generated-university")
                    ))
                
                # 5. Commit the transaction to save the data
                conn.commit()
                print("Migration complete! All records successfully inserted.")

    except Exception as e:
        print(f"An error occurred during migration: {e}")

if __name__ == "__main__":
    migrate_data()