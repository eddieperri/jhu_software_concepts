"""
Pytest fixtures and configuration for the Grad Cafe Analytics application.
Provides mocked database connections and fake data for testing microservices.
"""

import os
import sys
import json
import pytest
import psycopg
from dotenv import load_dotenv

# Ensure all microservice directories are on the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/web')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/worker')))

from run import create_app

@pytest.fixture
def app():
    """Creates a fresh Flask application configured for testing."""
    test_config = {
        'TESTING': True,
        'DATABASE_URL': os.environ.get('TEST_DATABASE_URL', 'postgresql://localhost/grad_cafe_test')
    }
    flask_app = create_app(test_config=test_config)
    yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def fake_metrics():
    """Dummy dictionary of metrics for frontend testing."""
    return {
        "q1": 150, "q2": 45.1234, "q3_gpa": 3.8, "q3_gre": 165,
        "q3_grev": 160, "q3_greaw": 4.5, "q4": 3.75, "q5": 22.8765,
        "q6": 3.9, "q7": 12, "q8": 5, "q9_raw": 3,
        "q10": [("MIT", 50), ("Stanford", 45)],
        "q11": [("March", 80), ("February", 60)]
    }

@pytest.fixture
def fake_json_data(tmp_path):
    """Creates a temporary JSON file containing fake applicant records."""
    test_data = [
        {
            "program": "Computer Science", "uGPA": "3.8", "GRE Quant": "165",
            "GRE Verbal": "160", "GRE AW": "4.5", "date added": "Added on May 29, 2026",
            "result url": "https://test.com/1", "status": "Accepted", "term": "Fall 2026",
            "I/International": "American", "Degree": "PhD",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Stanford University"
        }
    ]
    file_path = tmp_path / "test_applicant_data.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f)
    return str(file_path)

@pytest.fixture
def test_db():
    """Sets up a clean test database schema including the new watermarks table."""
    load_dotenv()
    if os.environ.get("GITHUB_ACTIONS") == "true":
        db_url = "postgresql://postgres:password@localhost:5432/postgres"
    else:
        db_url = "postgresql://postgres:1234@localhost:5432/postgres"
    
    os.environ['DATABASE_URL'] = db_url
    
    with psycopg.connect(conninfo=db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS applicants;")
            cur.execute("DROP TABLE IF EXISTS ingestion_watermarks;")
            cur.execute("""
                CREATE TABLE applicants (
                    p_id SERIAL PRIMARY KEY, program TEXT NOT NULL, comments TEXT,
                    date_added DATE, url TEXT UNIQUE NOT NULL, status TEXT NOT NULL,
                    term TEXT NOT NULL, us_or_international TEXT, gpa NUMERIC,
                    gre NUMERIC, gre_v NUMERIC, gre_aw NUMERIC, degree TEXT,
                    llm_generated_program TEXT, llm_generated_university TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE ingestion_watermarks (
                    source TEXT PRIMARY KEY, last_seen TEXT, updated_at TIMESTAMPTZ DEFAULT now()
                );
            """)
            cur.execute("INSERT INTO ingestion_watermarks (source, last_seen) VALUES ('gradcafe_scraper', '');")
        conn.commit()
    
    yield db_url
    
    with psycopg.connect(conninfo=db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS applicants;")
            cur.execute("DROP TABLE IF EXISTS ingestion_watermarks;")
        conn.commit()