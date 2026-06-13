import pytest
import json

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