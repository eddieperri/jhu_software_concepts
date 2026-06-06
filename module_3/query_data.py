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

def run_assignment_report():
    print("Running Assignment Analysis Report...\n")
    
    try:
        with psycopg.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                
                # Q1: Applied for Fall 2026
                cur.execute("SELECT COUNT(*) FROM applicants WHERE term = 'Fall 2026';")
                print(f"1. Total entries for Fall 2026: {cur.fetchone()[0]}")

                # Q2: Percentage of International Students
                cur.execute("""
                    SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE is_international = true) / NULLIF(COUNT(*), 0), 2) 
                    FROM applicants;
                """)
                print(f"2. Percentage of International Students: {cur.fetchone()[0]}%")

                # Q3: Average GPA, GRE (Sanitized)
                cur.execute("""
                    SELECT ROUND(AVG(gpa)::numeric, 2), ROUND(AVG(gre_q)::numeric, 1), 
                           ROUND(AVG(gre_v)::numeric, 1), ROUND(AVG(gre_aw)::numeric, 1)
                    FROM applicants 
                    WHERE (gpa IS NOT NULL AND gpa <= 4.0)
                    AND (gre_q BETWEEN 130 AND 170)
                    AND (gre_v BETWEEN 130 AND 170)
                    AND (gre_aw BETWEEN 0 AND 6.0);
                """)
                res = cur.fetchone()
                print(f"3. Averages: GPA: {res[0]}, GRE-Q: {res[1]}, GRE-V: {res[2]}, GRE-AW: {res[3]}")

                # Q4: Avg GPA of American Students in Fall 2026
                # (Assuming 'American' maps to is_international = false)
                cur.execute("""
                    SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants 
                    WHERE term = 'Fall 2026' AND is_international = false;
                """)
                print(f"4. Avg GPA of American Students (Fall 2026): {cur.fetchone()[0]}")

                # Q5: Percent Acceptance Fall 2026
                cur.execute("""
                    SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE status ILIKE 'Accepted%') / NULLIF(COUNT(*), 0), 2)
                    FROM applicants WHERE term = 'Fall 2026';
                """)
                print(f"5. Acceptance Rate (Fall 2026): {cur.fetchone()[0]}%")

                # Q6: Avg GPA of Acceptances Fall 2026
                cur.execute("""
                    SELECT ROUND(AVG(gpa)::numeric, 2) FROM applicants 
                    WHERE term = 'Fall 2026' AND status ILIKE 'Accepted%';
                """)
                print(f"6. Avg GPA of Acceptances (Fall 2026): {cur.fetchone()[0]}")

                # Q7: JHU, Masters, CS
                cur.execute("""
                    SELECT COUNT(*) FROM applicants 
                    WHERE llm_generated_university = 'Johns Hopkins University' 
                    AND degree = 'Masters' 
                    AND llm_generated_program ILIKE '%Computer Science%';
                """)
                print(f"7. JHU Masters in CS applicants: {cur.fetchone()[0]}")

                # Q8: Geo, MIT, Stanford, CMU, PhD in CS (Fall 2026)
                cur.execute("""
                    SELECT COUNT(*) FROM applicants 
                    WHERE term = 'Fall 2026' AND status ILIKE 'Accepted%' AND degree = 'PhD'
                    AND llm_generated_university IN ('Georgetown University', 'Massachusetts Institute of Technology', 'Stanford University', 'Carnegie Mellon University')
                    AND llm_generated_program ILIKE '%Computer Science%';
                """)
                print(f"8. Accepted PhD CS at Top Schools: {cur.fetchone()[0]}")

                # Q9: Comparison using LLM vs Downloaded
                # (You can just explain this in your PDF using the results from Q8)
                print("9. See PDF for LLM vs Downloaded field comparison logic.")



                # --- Additional Question 1: Top 5 Programs by Volume ---
                cur.execute("""
                    SELECT llm_generated_program, COUNT(*) as volume
                    FROM applicants
                    GROUP BY llm_generated_program
                    ORDER BY volume DESC
                    LIMIT 5;
                """)
                print("\n10. Top 5 Programs by Applicant Volume:")
                for row in cur.fetchall():
                    print(f"    - {row[0]}: {row[1]} applications")

                # --- Additional Question 2: Monthly Trends ---
                # This uses Postgres date parsing to group by month name
                cur.execute("""
                    SELECT 
                        TO_CHAR(TO_DATE(date_added, '"Added on" Mon DD, YYYY'), 'Month') as month_name, 
                        COUNT(*) as count 
                    FROM applicants 
                    GROUP BY month_name 
                    ORDER BY count DESC;
                """)
                print("\n11. Application Volume by Month:")
                for row in cur.fetchall():
                    print(f"    - {row[0].strip()}: {row[1]} entries")
                
                print("-" * 50)
                print("\nReport complete.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_assignment_report()