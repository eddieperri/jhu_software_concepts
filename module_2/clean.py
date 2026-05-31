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
    """RESCUE MODE: Skips LLM and just processes the already-completed .jsonl file."""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    clean_path = os.path.join(script_dir, "applicant_data.json")
    
    llm_dir = os.path.join(script_dir, "llm_hosting")
    temp_out = os.path.join(llm_dir, "temp_in.json.jsonl") 
    
    print("\nRescuing data from existing JSONL file...")
    final_data = []
    
    # 1. Open the 12-hour file that is already sitting on your hard drive
    try:
        with open(temp_out, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip(): 
                    final_data.append(json.loads(line)) 
    except FileNotFoundError:
        print(f"CRITICAL ERROR: Could not find {temp_out}. Did it get deleted?")
        return
                    
    # 2. Save the final file
    save_data(final_data, clean_path)
    
    print(f"Success! {len(final_data)} records rescued and saved to applicant_data.json.")


if __name__ == "__main__":
    clean_data()