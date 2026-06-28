"""
Pytest suite for verifying Flask routing and RabbitMQ publishing paths.
"""

import json
from unittest.mock import patch
import pytest

@pytest.mark.buttons
@patch('run.publish_task')
def test_pull_data_success(mock_publish, client):
    """Test POST /pull-data publishes task and returns 202."""
    response = client.post('/pull-data')
    assert response.status_code == 202
    data = json.loads(response.data)
    assert data.get("ok") is True
    mock_publish.assert_called_once_with("scrape_new_data", payload={})

@pytest.mark.buttons
@patch('run.publish_task')
def test_update_analysis_success(mock_publish, client):
    """Test POST /update-analysis publishes task and returns 202."""
    response = client.post('/update-analysis')
    assert response.status_code == 202
    data = json.loads(response.data)
    assert data.get("ok") is True
    mock_publish.assert_called_once_with("recompute_analytics", payload={})

@pytest.mark.buttons
@patch('run.publish_task')
def test_pull_data_failure(mock_publish, client):
    """Test 503 error path when RabbitMQ is down."""
    mock_publish.side_effect = Exception("RabbitMQ Connection Refused")
    response = client.post('/pull-data')
    assert response.status_code == 503
    data = json.loads(response.data)
    assert "error" in data

@pytest.mark.buttons
@patch('run.publish_task')
def test_update_analysis_failure(mock_publish, client):
    """Test 503 error path when RabbitMQ is down."""
    mock_publish.side_effect = Exception("RabbitMQ Connection Refused")
    response = client.post('/update-analysis')
    assert response.status_code == 503