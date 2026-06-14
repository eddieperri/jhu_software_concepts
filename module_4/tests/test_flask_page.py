"""
Pytest suite for verifying Flask application routing and HTML rendering.
Ensures the factory pattern works, routes are active, and UI components render with stable selectors.
"""

import pytest
from bs4 import BeautifulSoup
import flask_app 
import json

@pytest.mark.web
def test_app_factory_and_routes(app):
    """
    Test app factory / Config: Assert a testable Flask app is created 
    with required routes.
    """
    # Verify the test configuration was loaded
    assert app.config['TESTING'] is True
    
    # Verify all expected routes exist in the Flask application
    routes = [rule.rule for rule in app.url_map.iter_rules()]
    assert '/analysis' in routes
    assert '/pull-data' in routes
    assert '/update-analysis' in routes

@pytest.mark.web
def test_analysis_page_rendering(client, monkeypatch, fake_metrics):
    """
    Test GET /analysis (page load)
    - Status 200
    - Page Contains both buttons
    - Page text includes "Analysis" and at least one "Answer:"
    """
    # 1. Dependency Injection: Swap out the real database call with our fake data
    # <-- Changed src.flask_app to flask_app here
    monkeypatch.setattr(flask_app, 'get_metrics', lambda: fake_metrics) 
    
    # 2. Simulate a user visiting the page
    response = client.get('/analysis')
    
    # Assert Status 200
    assert response.status_code == 200
    
    # Parse the HTML using BeautifulSoup for stable UI assertions
    html_text = response.data.decode('utf-8')
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # Assert Page text includes "Analysis" and "Answer:"
    assert "Analysis" in html_text
    assert "Answer:" in html_text
    
    # Assert Buttons Exist using the stable data-testid selectors we added
    pull_btn = soup.find('button', {'data-testid': 'pull-data-btn'})
    update_btn = soup.find('button', {'data-testid': 'update-analysis-btn'})
    
    assert pull_btn is not None
    assert "Pull Data" in pull_btn.text
    
    assert update_btn is not None
    assert "Update Analysis" in update_btn.text

@pytest.mark.web
def test_home_redirect(client):
    """
    Test that navigating to the root URL (/) correctly redirects
    the user to the /analysis dashboard.
    """
    response = client.get('/')
    
    # 302 is the standard HTTP status code for a redirect
    assert response.status_code == 302
    
    # Verify that the location it redirects to is the analysis page
    assert '/analysis' in response.location

@pytest.mark.web
def test_status_endpoint(client):
    """
    Test GET /status returns 200 and the correct JSON structure.
    """
    response = client.get('/status')
    
    # Verify the route is accessible
    assert response.status_code == 200
    
    # Verify it returns the expected boolean state
    data = json.loads(response.data)
    assert "is_scraping" in data
    assert data["is_scraping"] is False