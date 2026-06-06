import json

def inspect_data(filepath):
    print(f"Inspecting {filepath} for bad data...")
    with open(filepath, 'r', encoding='utf-8') as file:
        data = json.load(file)

    for i, row in enumerate(data):
        gpa = float(row.get("uGPA", 0)) if row.get("uGPA") else 0
        
        # Check for impossible values
        if gpa > 4.0:
            print(f"Suspicious GPA found at record {i}: {gpa} (Program: {row.get('program')})")
            
        # Check GRE scores (if present)
        # Assuming we are checking keys "GRE Quant"
        gre_q = float(row.get("GRE Quant", 0)) if row.get("GRE Quant") else 0
        if gre_q > 170:
            print(f"Suspicious GRE Quant found at record {i}: {gre_q} (Program: {row.get('program')})")

if __name__ == "__main__":
    # Point to the subfolder where your JSON lives
    inspect_data('web_scraping/raw_data.json')