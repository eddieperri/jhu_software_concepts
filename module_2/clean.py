import json
import os
import subprocess
import sys

def load_data(filepath):
    """Loads the scraped data."""
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Error: Could not find {filepath}.")
        return None

def save_data(data, filepath):
    """Saves data to a JSON file."""
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def clean_data():
    """Formats raw data and triggers the LLM standardization."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(script_dir, "raw_data.json")
    clean_path = os.path.join(script_dir, "applicant_data.json")
    
    llm_dir = os.path.join(script_dir, "llm_hosting")
    temp_in = os.path.join(llm_dir, "temp_in.json")
    temp_out = os.path.join(llm_dir, "temp_in.jsonl")
    app_script = os.path.join(llm_dir, "app.py")
    
    raw_data = load_data(raw_path)
    if not raw_data: return
    # --- DEDUPLICATION LOGIC ---
    seen = set()
    unique_raw_data = []
    
    for record in raw_data:
        # Convert the dictionary to a sorted string so it can be tracked
        record_string = json.dumps(record, sort_keys=True)
        if record_string not in seen:
            seen.add(record_string)
            unique_raw_data.append(record)
            
    print(f"Loaded {len(raw_data)} records. Removed {len(raw_data) - len(unique_raw_data)} exact duplicates.")
    raw_data = unique_raw_data
    # ---------------------------    
    formatted_data = []
    
    # Map raw keys to the Rubric's required keys
    for record in raw_data:
        clean_record = {
            "program": record["raw_program"], 
            "comments": record["comments"],
            "date added": f"Added on {record['added_on']}",
            "result url": record["url"],
            "status": record["decision"],
            "term": record["term"],
            "I/International": record["international"],
            "Degree": record["degree"],
            "raw_text_traceability": record["raw_program"] # Rubric trace requirement
        }
        
        if record["gpa"]: clean_record["uGPA"] = record["gpa"]
        if record["gre_quant"]: clean_record["GRE Quant"] = record["gre_quant"]
        if record["gre_verbal"]: clean_record["GRE Verbal"] = record["gre_verbal"]
        if record["gre_aw"]: clean_record["GRE AW"] = record["gre_aw"]
            
        formatted_data.append(clean_record)

    save_data(formatted_data, temp_in)
    print(f"Formatted {len(formatted_data)} records. Triggering local LLM...")
    
    env = os.environ.copy()
    env["N_THREADS"] = "2" 
    
    try:
        # Run the professor's script using the EXACT same Python engine
        subprocess.run(
            [sys.executable, app_script, "--file", temp_in],
            env=env,
            cwd=llm_dir, 
            check=True
        )
    except subprocess.CalledProcessError:
        print("Error: The LLM standardizer crashed.")
        return

    # Validates output and formats as standard JSON array
    print("\nValidating JSON output...")
    final_data = []
    with open(temp_out, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                final_data.append(json.loads(line))
                
    save_data(final_data, clean_path)
    
    if os.path.exists(temp_in): os.remove(temp_in)
    if os.path.exists(temp_out): os.remove(temp_out)
    
    print(f"Success! {len(final_data)} records cleaned and saved to applicant_data.json.")

if __name__ == "__main__":
    clean_data()