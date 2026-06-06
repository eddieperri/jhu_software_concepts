import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

DB_PARAMS = {
    "dbname": "thegradcafe",
    "user": "postgres",
    "password": os.environ.get("DB_PASSWORD"), 
    "host": "localhost",
    "port": 5432
}

def get_metrics():
    """Runs analysis, prints the report to the terminal, and returns a dict for Flask."""
    print("Running Assignment Analysis Report...\n")
    print("-" * 50)
    
    metrics = {}
    
    try:
        with psycopg.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                
                # Q1: Applied for Fall 2026
                cur.execute("SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2026';")
                metrics['q1'] = cur.fetchone()[0]
                print(f"1. Total entries for Fall 2026: {metrics['q1']}")

                # Q2: Percentage of International Students
                cur.execute("""
                    SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE us_or_international = 'International') / NULLIF(COUNT(*), 0), 2) 
                    FROM applicants;
                """)
                metrics['q2'] = cur.fetchone()[0]
                print(f"2. Percentage of International Students: {metrics['q2']}%")

                # Q3: Average GPA, GRE (Sanitized)
                cur.execute("""
                    SELECT ROUND(AVG(gpa)::numeric, 2), ROUND(AVG(gre)::numeric, 1), 
                           ROUND(AVG(gre_v)::numeric, 1), ROUND(AVG(gre_aw)::numeric, 1)
                    FROM applicants 
                    WHERE (gpa IS NOT NULL AND gpa <= 4.0)
                    AND (gre BETWEEN 130 AND 170)
                    AND (gre_v BETWEEN 130 AND 170)
                    AND (gre_aw BETWEEN 0 AND 6.0);
                """)
                res = cur.fetchone()
                metrics['q3_gpa'] = res[0]
                metrics['q3_gre'] = res[1]
                metrics['q3_grev'] = res[2]
                metrics['q3_greaw'] = res[3]
                print(f"3. Averages: GPA: {res[0]}, GRE-Q: {res[1]}, GRE-V: {res[2]}, GRE-AW: {res[3]}")

                # Q4: Avg GPA of American Students in Fall 2026
                cur.execute("""
                    SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants 
                    WHERE term = 'Fall 2026' AND us_or_international = 'American';
                """)
                metrics['q4'] = cur.fetchone()[0]
                print(f"4. Avg GPA of American Students (Fall 2026): {metrics['q4']}")

                # Q5: Percent Acceptance Fall 2026
                cur.execute("""
                    SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status ILIKE 'Accepted%') / NULLIF(COUNT(*), 0), 2)
                    FROM applicants WHERE term = 'Fall 2026';
                """)
                metrics['q5'] = cur.fetchone()[0]
                print(f"5. Acceptance Rate (Fall 2026): {metrics['q5']}%")

                # Q6: Avg GPA of Acceptances Fall 2026
                cur.execute("""
                    SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants 
                    WHERE term = 'Fall 2026' AND status ILIKE 'Accepted%';
                """)
                metrics['q6'] = cur.fetchone()[0]
                print(f"6. Avg GPA of Acceptances (Fall 2026): {metrics['q6']}")

                # Q7: JHU, Masters, CS
                cur.execute("""
                    SELECT COUNT(*) FROM applicants 
                    WHERE llm_generated_university = 'Johns Hopkins University' 
                    AND degree = 'Masters' 
                    AND llm_generated_program ILIKE '%Computer Science%';
                """)
                metrics['q7'] = cur.fetchone()[0]
                print(f"7. JHU Masters in CS applicants: {metrics['q7']}")

                # Q8: Geo, MIT, Stanford, CMU, PhD in CS (Fall 2026)
                cur.execute("""
                    SELECT COUNT(*) FROM applicants 
                    WHERE term = 'Fall 2026' AND status ILIKE 'Accepted%' AND degree = 'PhD'
                    AND llm_generated_university IN ('Georgetown University', 'Massachusetts Institute of Technology', 'Stanford University', 'Carnegie Mellon University')
                    AND llm_generated_program ILIKE '%Computer Science%';
                """)
                metrics['q8'] = cur.fetchone()[0]
                print(f"8. Accepted PhD CS at Top Schools (Using LLM Fields): {metrics['q8']}")

                # Q9: Comparison using LLM vs Downloaded Raw Text
                cur.execute("""
                    SELECT COUNT(*) FROM applicants 
                    WHERE term = 'Fall 2026' AND status ILIKE 'Accepted%' AND degree = 'PhD'
                    AND program ILIKE '%Computer Science%'
                    AND (program ILIKE '%Georgetown%' 
                         OR program ILIKE '%Massachusetts Institute of Technology%' 
                         OR program ILIKE '%MIT%' 
                         OR program ILIKE '%Stanford%' 
                         OR program ILIKE '%Carnegie Mellon%');
                """)
                metrics['q9_raw'] = cur.fetchone()[0]
                print("9. Comparison (LLM vs Raw Text):")
                print(f"   - Acceptances captured using Standardized LLM Fields: {metrics['q8']}")
                print(f"   - Acceptances captured using Raw User-Input Fields: {metrics['q9_raw']}")

                # --- Additional Question 1: Top 5 Programs by Volume ---
                cur.execute("""
                    SELECT llm_generated_program, COUNT(*) as volume
                    FROM applicants
                    GROUP BY llm_generated_program
                    ORDER BY volume DESC
                    LIMIT 5;
                """)
                metrics['q10'] = cur.fetchall()
                print("\n10. Top 5 Programs by Applicant Volume:")
                for row in metrics['q10']:
                    print(f"    - {row[0]}: {row[1]} applications")

                # --- Additional Question 2: Monthly Trends ---
                cur.execute("""
                    SELECT 
                        TO_CHAR(date_added, 'Month') as month_name, 
                        COUNT(*) as count 
                    FROM applicants 
                    GROUP BY month_name 
                    ORDER BY count DESC;
                """)
                metrics['q11'] = cur.fetchall()
                print("\n11. Application Volume by Month:")
                for row in metrics['q11']:
                    print(f"    - {row[0].strip()}: {row[1]} entries")
                
                print("-" * 50)
                print("Report complete.\n")

    except Exception as e:
        print(f"An error occurred: {e}")
        
    return metrics

if __name__ == "__main__":
    # If run directly from the terminal, it will execute and print.
    get_metrics()