"""
Pytest suite for verifying Flask application routing and HTML rendering.
Ensures the factory pattern works, routes are active, and UI components render with stable selectors.
"""

import pytest
from bs4 import BeautifulSoup

@pytest.mark.web
def test_app_factory_and_routes(app):
    """
    Test app factory / Config: Assert a testable Flask app is created 
    with required routes.
    """
    assert app.config['TESTING'] is True
    
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
    # Swap out the real database call with our fake data targeting the new run module
    monkeypatch.setattr('run.get_metrics', lambda: fake_metrics) 
    
    response = client.get('/analysis')
    assert response.status_code == 200
    
    html_text = response.data.decode('utf-8')
    soup = BeautifulSoup(html_text, 'html.parser')
    
    assert "Analysis" in html_text
    assert "Answer:" in html_text
    
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
    assert response.status_code == 302
    assert '/analysis' in response.location