import pytest
import os
import sys
import json
import psycopg
from dotenv import load_dotenv

# Ensure the src directory is on the Python path so we can import flask_app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from flask_app import create_app

@pytest.fixture
def mock_pipeline_runner():
    """
    A fake pipeline runner that instantly completes without hitting the network.
    This fulfills the dependency injection requirement and prevents live scraping.
    """
    def fake_runner(app_instance):
        # We simulate the busy state locking, but complete instantly
        app_instance.config['IS_SCRAPING'] = True
        app_instance.config['IS_SCRAPING'] = False
    return fake_runner

@pytest.fixture
def app(mock_pipeline_runner):
    """
    Creates a fresh Flask application configured for testing.
    """
    # Overriding standard config to use a test database and enable testing mode
    test_config = {
        'TESTING': True,
        'DATABASE_URL': os.environ.get('TEST_DATABASE_URL', 'postgresql://localhost/grad_cafe_test')
    }
    
    # We pass the test config and inject our mock runner
    app = create_app(test_config=test_config, pipeline_runner=mock_pipeline_runner)
    
    yield app

@pytest.fixture
def client(app):
    """
    A test client for the app, allowing us to simulate GET and POST requests.
    """
    return app.test_client()

@pytest.fixture
def fake_metrics():
    """
    A fixture that returns a dummy dictionary of metrics so we can test 
    the frontend rendering without needing real database data.
    """
    return {
        "q1": 150,
        "q2": 45.1234, # Intentionally more than 2 decimals to test rounding
        "q3_gpa": 3.8,
        "q3_gre": 165,
        "q3_grev": 160,
        "q3_greaw": 4.5,
        "q4": 3.75,
        "q5": 22.8765, # Intentionally more than 2 decimals
        "q6": 3.9,
        "q7": 12,
        "q8": 5,
        "q9_raw": 3,
        "q10": [("MIT", 50), ("Stanford", 45), ("CMU", 40), ("Berkeley", 35), ("JHU", 30)],
        "q11": [("March", 80), ("February", 60), ("April", 40)]
    }

@pytest.fixture
def fake_json_data(tmp_path):
    """
    Creates a temporary JSON file containing 2 fake applicant records.
    This prevents testing against the massive 50,000 row live dataset.
    """
    test_data = [
        {
            "program": "Computer Science",
            "uGPA": "3.8",
            "GRE Quant": "165",
            "GRE Verbal": "160",
            "GRE AW": "4.5",
            "date added": "Added on May 29, 2026",
            "result url": "https://test.com/1",
            "status": "Accepted",
            "term": "Fall 2026",
            "I/International": "American",
            "Degree": "PhD",
            "llm-generated-program": "Computer Science",
            "llm-generated-university": "Stanford University"
        },
        {
            "program": "Biology",
            "uGPA": "4.1", # Intentionally bad GPA to test cleaning
            "GRE Quant": "abc", # Intentionally bad GRE to test cleaning
            "GRE Verbal": "160",
            "GRE AW": "4.5",
            "date added": "Bad Date String",
            "result url": "https://test.com/2",
            "status": "Rejected",
            "term": "Fall 2026",
            "I/International": "International",
            "Degree": "Masters",
            "llm-generated-program": "Biology",
            "llm-generated-university": "MIT"
        }
    ]
    
    # tmp_path is a built-in Pytest fixture that provides a temporary directory
    file_path = tmp_path / "test_applicant_data.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f)
        
    return str(file_path)

@pytest.fixture
def test_db():
    """
    Sets up a clean test database schema and yields the URL.
    Tears down the table after the test is complete.
    """
    load_dotenv()
    
    # 1. Detect if we are running in GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # CI Environment: Use the default password defined in our tests.yml
        db_url = "postgresql://postgres:password@localhost:5432/postgres"
    else:
        # Local Environment: Use your secure .env password
        db_password = os.environ.get("DB_PASSWORD", "")
        db_url = f"postgresql://postgres:{db_password}@localhost:5432/postgres"
    
    # 2. Set the environment variable so all source code uses it
    os.environ['DATABASE_URL'] = db_url
    
    # Setup schema
    with psycopg.connect(conninfo=db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS applicants;")
            cur.execute("""
                CREATE TABLE applicants (
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
        conn.commit()
    
    yield db_url
    
    # Teardown
    with psycopg.connect(conninfo=db_url) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS applicants;")
        conn.commit()