import json

def inspect_data(filepath):
    """
    Loads the JSON dataset and validates numeric values.
    Identifies potential data entry errors or scraping artifacts
    that fall outside of standard logical ranges.
    """
    print(f"Inspecting {filepath} for bad data...")

    # Load the JSON file into a list of dictionaries
    with open(filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)

    for i, row in enumerate(data):
        # Attempt to cast uGPA to float; default to 0 if key is missing or null
        gpa = float(row.get("uGPA", 0)) if row.get("uGPA") else 0
        
        # Check for impossible values
        if gpa > 4.0:
            print(f"Suspicious GPA found at record {i}: {gpa} (Program: {row.get('program')})")
            
        # Validate GRE Quant scores (Standard range is 130-170)
        # Assuming we are checking the "GRE Quant" key from the scraper output
        gre_q = float(row.get("GRE Quant", 0)) if row.get("GRE Quant") else 0
        if gre_q > 170:
            print(f"Suspicious GRE Quant found at record {i}: {gre_q} (Program: {row.get('program')})")

if __name__ == "__main__":
    # Point to the subfolder where your JSON lives
    inspect_data('web_scraping/raw_data.json')