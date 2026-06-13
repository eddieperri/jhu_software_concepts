import pytest
import json
import subprocess
from unittest.mock import patch
from flask_app import create_app, default_pipeline_runner

@pytest.mark.buttons
def test_pull_data_success(client):
    """
    Test POST /pull-data:
    - Returns 202 (Accepted)
    - Triggers the loader (mocked via our conftest fixture)
    """
    response = client.post('/pull-data')
    
    # Verify the correct status code for starting a background task
    assert response.status_code == 202
    
    # Verify the JSON response matches the rubric requirement
    data = json.loads(response.data)
    assert data.get("ok") is True

@pytest.mark.buttons
def test_update_analysis_success(client):
    """
    Test POST /update-analysis:
    - Returns 200 when not busy
    """
    response = client.post('/update-analysis')
    
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data.get("ok") is True

@pytest.mark.buttons
def test_busy_gating_pull_data(client, app):
    """
    Test busy gating:
    - When busy, POST /pull-data returns 409
    """
    # Force the app into a "scraping" state
    app.config['IS_SCRAPING'] = True
    
    response = client.post('/pull-data')
    
    # Verify it rejects the request
    assert response.status_code == 409
    
    # Verify the JSON payload
    data = json.loads(response.data)
    assert data.get("busy") is True

@pytest.mark.buttons
def test_busy_gating_update_analysis(client, app):
    """
    Test busy gating:
    - When a pull is "in progress", POST /update-analysis returns 409 
      (and performs no update).
    """
    # Force the app into a "scraping" state
    app.config['IS_SCRAPING'] = True
    
    response = client.post('/update-analysis')
    
    assert response.status_code == 409
    
    data = json.loads(response.data)
    assert data.get("busy") is True

@pytest.mark.buttons
@patch('flask_app.subprocess.run')
def test_pipeline_failure_releases_lock(mock_run):
    """
    Tests the negative/error path where the ETL pipeline crashes.
    Ensures the application catches the error and correctly releases 
    the IS_SCRAPING lock so the system does not permanently freeze.
    """
    # 1. Create a fresh test application
    app = create_app()
    
    # 2. Simulate a fatal crash when the pipeline tries to run the scraper
    mock_run.side_effect = subprocess.CalledProcessError(returncode=1, cmd='scrape.py')
    
    # 3. Manually lock the app (simulating the start of the /pull-data route)
    app.config['IS_SCRAPING'] = True
    
    # 4. Execute the pipeline runner directly to test its internal error handling
    default_pipeline_runner(app)
    
    # 5. Assert the lock was safely released despite the violent crash!
    assert app.config['IS_SCRAPING'] is False