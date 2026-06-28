"""
Pytest suite for verifying the HTML rendering and formatting of the analysis dashboard.
Ensures UI elements are properly labeled and mathematical outputs are strictly rounded.
"""

import re
import pytest
from bs4 import BeautifulSoup

@pytest.mark.analysis
def test_analysis_labels_and_rounding(client, monkeypatch, fake_metrics):
    """
    Test analysis formatting:
    - Rendered items are labeled with "Answer:"
    - Any percentage rendered on the page is shown with exactly two decimals.
    """
    # Swap out the real database call with our fake data using the new run.py module
    monkeypatch.setattr('run.get_metrics', lambda: fake_metrics)
    
    response = client.get('/analysis')
    html_text = response.data.decode('utf-8')
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # --- 1. Test Labels ---
    answer_labels = soup.find_all('span', class_='answer-label')
    assert len(answer_labels) > 0, "No 'Answer:' labels found on the page."
    for label in answer_labels:
        assert "Answer:" in label.text
        
    # --- 2. Test Rounding (Regex) ---
    percentage_texts = re.findall(r'(\d+\.\d+)%', html_text)
    assert len(percentage_texts) > 0, "No percentages found on the page to test."
    
    for num_str in percentage_texts:
        decimals = num_str.split('.')[1]
        assert len(decimals) == 2, f"Found a percentage with invalid decimal precision: {num_str}%"