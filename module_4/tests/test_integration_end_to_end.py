import pytest
import json
import os
import subprocess
import psycopg
import flask_app
import load_data
import query_data
import inspect_data

@pytest.mark.integration
def test_end_to_end_flow(client, app, test_db, fake_json_data, monkeypatch):
    """
    End-to-end (pull -> update -> Render)
    """
    # 1. Mock subprocess.run to inject our fake scraper logic.
    # When the app tries to run 'load_data.py', we intercept it and pass our fake JSON instead.
    def mock_subprocess_run(args, **kwargs):
        if "load_data.py" in str(args):
            load_data.load_data(fake_json_data)
            
    monkeypatch.setattr(subprocess, 'run', mock_subprocess_run)
    
    # POST /pull-data triggers a background thread, but to test the actual pipeline 
    # synchronously without race conditions, we call the runner directly:
    flask_app.default_pipeline_runner(app)
    
    # Verify 3 rows were inserted by the pipeline
    with psycopg.connect(conninfo=test_db) as conn:
        with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM applicants;")
                # Update this from 2 to 3
                assert cur.fetchone()[0] == 3
            
    # Run the pipeline again to test your uniqueness constraint (idempotency)
    flask_app.default_pipeline_runner(app)
 # Verify the database STILL only has 3 rows (no duplicates)
    with psycopg.connect(conninfo=test_db) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM applicants;")
                # Updated this from 2 to 3
                assert cur.fetchone()[0] == 3
            
    # 2. POST /update-analysis endpoint works when idle
    resp_update = client.post('/update-analysis')
    assert resp_update.status_code == 200
    
    # 3. GET /analysis shows the updated database data
    resp_get = client.get('/analysis')
    html = resp_get.data.decode('utf-8')
    assert "Applicant count: 3" in html

@pytest.mark.integration
def test_error_paths_for_100_coverage(monkeypatch, app, tmp_path):
    """
    Intentionally triggers all exception blocks to guarantee 100% coverage.
    """
    # --- 1. inspect_data.py & load_data.py edge cases ---
    # We create a record with bad GPA/GRE (for inspect_data) 
    # and a blank url / bad date (to trigger the load_data `continue` block)
    suspicious_data = [{
        "uGPA": "4.5", 
        "GRE Quant": "175", 
        "program": "CS",
        "date added": "Added on BadDate", 
        "result url": ""  
    }]
    test_file = tmp_path / "inspect.json"
    with open(test_file, "w") as f:
        json.dump(suspicious_data, f)
        
    inspect_data.inspect_data(str(test_file))
    load_data.load_data(str(test_file))
    
    # Test clean_numeric TypeError
    assert load_data.clean_numeric(["invalid"], 0, 4) is None
    
    # --- 2. flask_app.py subprocess errors ---
    def mock_cpe(*args, **kwargs):
        raise subprocess.CalledProcessError(1, 'cmd')
    monkeypatch.setattr(subprocess, 'run', mock_cpe)
    flask_app.default_pipeline_runner(app) # Triggers except CalledProcessError
    
    def mock_exc(*args, **kwargs):
        raise Exception("Simulated Failure")
    monkeypatch.setattr(subprocess, 'run', mock_exc)
    flask_app.default_pipeline_runner(app) # Triggers except Exception
    
    # --- 3. Database & File path errors ---
    with pytest.raises(FileNotFoundError):
        load_data.load_data("definitely_does_not_exist.json")
        
    # Corrupt the DB URL to force psycopg connection exceptions
    monkeypatch.setattr(os, 'environ', {'DATABASE_URL': 'postgresql://bogus:123'})
    with pytest.raises(Exception):
        load_data.load_data(str(test_file))
    with pytest.raises(Exception):
        query_data.get_metrics()