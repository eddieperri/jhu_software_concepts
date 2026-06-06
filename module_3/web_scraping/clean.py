import json
import os
import subprocess
import sys

def load_data(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return []

def save_data(data, filepath):
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def clean_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(script_dir, "raw_data.json")
    clean_path = os.path.join(script_dir, "applicant_data.json")
    
    llm_dir = os.path.join(script_dir, "llm_hosting")
    temp_in = os.path.join(llm_dir, "temp_in.json")
    temp_out = os.path.join(llm_dir, "temp_in.json.jsonl")
    app_script = os.path.join(llm_dir, "app.py")
    
    raw_data = load_data(raw_path)
    clean_data_existing = load_data(clean_path)
    
    # 1. Create a watchlist of URLs we have already processed through the LLM
    processed_urls = {record["result url"] for record in clean_data_existing}
    
    # 2. Filter: Only keep raw records whose URL is NOT in our clean list
    new_records = [r for r in raw_data if r["url"] not in processed_urls]
    
    if not new_records:
        print("No new records to standardize. Database is up to date.")
        return

    print(f"Found {len(new_records)} new records to process.")

    # 3. Format only the NEW records
    formatted_data = []
    for record in new_records:
        clean_record = {
            "program": record["raw_program"], 
            "comments": record["comments"],
            "date added": f"Added on {record['added_on']}",
            "result url": record["url"],
            "status": record["decision"],
            "term": record["term"],
            "I/International": record["international"],
            "Degree": record["degree"],
            "raw_text_traceability": record["raw_program"]
        }
        if record["gpa"]: clean_record["uGPA"] = record["gpa"]
        if record["gre_quant"]: clean_record["GRE Quant"] = record["gre_quant"]
        if record["gre_verbal"]: clean_record["GRE Verbal"] = record["gre_verbal"]
        if record["gre_aw"]: clean_record["GRE AW"] = record["gre_aw"]
        formatted_data.append(clean_record)

    save_data(formatted_data, temp_in)
    
    # Trigger LLM (Same as before)
    env = os.environ.copy()
    env["N_THREADS"] = "2"
    subprocess.run([sys.executable, app_script, "--file", temp_in], env=env, cwd=llm_dir, check=True)

    # 4. Append new results to existing cleaned file
    with open(temp_out, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                clean_data_existing.append(json.loads(line))
                
    save_data(clean_data_existing, clean_path)
    if os.path.exists(temp_in): os.remove(temp_in)
    if os.path.exists(temp_out): os.remove(temp_out)
    
    print(f"Success! {len(new_records)} records standardized and appended.")

if __name__ == "__main__":
    clean_data()