import json
import os
import subprocess
import sys

def load_data(filepath):
    """Loads the scraped data."""
    try:
        # 'r' stands for read mode. loads the raw_data.json into Python's memory
        with open(filepath, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        # if there is no file, return None as the filepath
        print(f"Error: Could not find {filepath}.")
        return None

def save_data(data, filepath):
    """Saves data to a JSON file"""
    # 'w' stands for write mode. indent=4 makes the JSON visually readable instead of one giant block of text.
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

def clean_data():
    """Formats raw data and triggers the LLM standardization."""

    # same automatic path finding as the scraping
    script_dir = os.path.dirname(os.path.abspath(__file__))
    raw_path = os.path.join(script_dir, "raw_data.json")
    clean_path = os.path.join(script_dir, "applicant_data.json")
    
    # Points to the hidden module_2/llm_hosting folder
    llm_dir = os.path.join(script_dir, "llm_hosting")
    temp_in = os.path.join(llm_dir, "temp_in.json")
    temp_out = os.path.join(llm_dir, "temp_in.json.jsonl") # .jsonl is like .json except one dictionary per line
    app_script = os.path.join(llm_dir, "app.py")
    
    raw_data = load_data(raw_path)
    if not raw_data: return


    # Deplicate Deleter
    seen = set() # sets can't hold duplicate item
    unique_raw_data = []
    
    for record in raw_data:
        # dictionaries cannot be added to sets directly so we convert the dictionary into an alphabetical text string (sort_keys=True)
        record_string = json.dumps(record, sort_keys=True)
        
        # if we haven't seen this exact text string before, add it to the tracking set and our final list.
        if record_string not in seen:
            seen.add(record_string)
            unique_raw_data.append(record)
            
    print(f"Loaded {len(raw_data)} records. Removed {len(raw_data) - len(unique_raw_data)} exact duplicates.")
    raw_data = unique_raw_data # Overwrite our working variable with the clean data
    

    formatted_data = []
    
    # Map our raw GradCafe keys to better key names
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
            "raw_text_traceability": record["raw_program"] # keeps the original text safe just in case the LLM breaks it
        }
        
        # Only add the test scores IF they actually exist. If the student left them blank, don't create an empty key
        if record["gpa"]: clean_record["uGPA"] = record["gpa"]
        if record["gre_quant"]: clean_record["GRE Quant"] = record["gre_quant"]
        if record["gre_verbal"]: clean_record["GRE Verbal"] = record["gre_verbal"]
        if record["gre_aw"]: clean_record["GRE AW"] = record["gre_aw"]
            
        formatted_data.append(clean_record)

    # Save the rubric-formatted data to a temporary file so the LLM can read it
    save_data(formatted_data, temp_in)
    print(f"Formatted {len(formatted_data)} records. Triggering local LLM...")
    
    # LLM Stuff
    # Copies your computer's current environment variables so the LLM knows what to do
    env = os.environ.copy()
    env["N_THREADS"] = "2" # number of cpu threads you want to use for the LLM
    
    try:
        # basically runs "python app.py --file temp_in.json"
        subprocess.run(
            [sys.executable, app_script, "--file", temp_in], # sys.executable forces it to use your current 'venv' Python
            env=env,
            cwd=llm_dir, # pretends the terminal is inside the llm_hosting folder
            check=True   # if the LLM crashes, so we don't save empty data
        )
    except subprocess.CalledProcessError:
        print("Error: The LLM standardizer crashed.")
        return

    # Data Validation and CLeaning
    print("\nValidating JSON output...")
    final_data = []
    
    # The LLM spit out a .jsonl file (one student per line). We read it line-by-line.
    with open(temp_out, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip(): # if the line isn't blank, 
                final_data.append(json.loads(line)) # ^convert the text string into a Python dictionary
                
    # save the final file
    save_data(final_data, clean_path)
    
    # delete the temporary files
    if os.path.exists(temp_in): os.remove(temp_in)
    if os.path.exists(temp_out): os.remove(temp_out)
    
    print(f"Success! {len(final_data)} records cleaned and saved to applicant_data.json.")

if __name__ == "__main__":
    clean_data()