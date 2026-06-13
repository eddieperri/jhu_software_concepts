import pytest
import re
from bs4 import BeautifulSoup
import flask_app

@pytest.mark.analysis
def test_analysis_labels_and_rounding(client, monkeypatch, fake_metrics):
    """
    Test analysis formatting:
    - Rendered items are labeled with "Answer:"
    - Any percentage rendered on the page is shown with exactly two decimals.
    """
    # Swap out the real database call with our fake data (which has messy >2 decimal percentages)
    monkeypatch.setattr(flask_app, 'get_metrics', lambda: fake_metrics)
    
    response = client.get('/analysis')
    html_text = response.data.decode('utf-8')
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # --- 1. Test Labels ---
    # Find all elements with the 'answer-label' class we added to the HTML
    answer_labels = soup.find_all('span', class_='answer-label')
    assert len(answer_labels) > 0, "No 'Answer:' labels found on the page."
    for label in answer_labels:
        assert "Answer:" in label.text
        
    # --- 2. Test Rounding (Regex) ---
    # This regex finds any numbers immediately followed by a '%' sign (e.g., "45.12%")
    # It captures the number portion so we can inspect it.
    percentage_texts = re.findall(r'(\d+\.\d+)%', html_text)
    
    assert len(percentage_texts) > 0, "No percentages found on the page to test."
    
    for num_str in percentage_texts:
        # Split the string by the decimal point and measure the length of the right side
        decimals = num_str.split('.')[1]
        assert len(decimals) == 2, f"Found a percentage with invalid decimal precision: {num_str}%"