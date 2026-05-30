import urllib.parse
import time
import random
import os
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def initialize_driver():
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    return webdriver.Chrome(options=options)

def _parse_html_to_dicts(raw_html):
    """Private helper method to parse the GradCafe HTML into raw dictionaries."""
    soup = BeautifulSoup(raw_html, 'html.parser')
    tbodies = soup.find_all('tbody')
    parsed_records = []
    
    for tbody in tbodies:
        rows = tbody.find_all('tr', recursive=False)
        current_record = None
        
        for row in rows:
            classes = row.get('class', [])
            
            # 1. MAIN ROW
            if 'tw-border-none' not in classes:
                if current_record:
                    parsed_records.append(current_record)
                
                tds = row.find_all('td', recursive=False)
                if len(tds) < 5: continue
                
                school = tds[0].text.strip()
                spans = tds[1].find_all('span')
                program = spans[0].text.strip() if len(spans) > 0 else ""
                degree = spans[1].text.strip() if len(spans) > 1 else ""
                added_on = tds[2].text.strip()
                decision = tds[3].text.strip()
                
                a_tag = row.find('a', href=True)
                url = "https://www.thegradcafe.com" + a_tag['href'] if a_tag else ""
                
                current_record = {
                    "raw_program": f"{program}, {school}", # Preserved for traceability
                    "school": school,
                    "program": program,
                    "degree": degree,
                    "added_on": added_on,
                    "decision": decision,
                    "url": url,
                    "comments": "",
                    "term": "",
                    "international": "",
                    "gpa": "",
                    "gre_quant": "",
                    "gre_verbal": "",
                    "gre_aw": ""
                }
            
            # 2. DETAILS ROW (Badges or Comments)
            else:
                if not current_record: continue
                
                badges = row.find_all('div', class_='tw-inline-flex')
                for badge in badges:
                    text = badge.text.strip()
                    if any(term in text for term in ["Fall", "Spring", "Summer", "Winter"]):
                        current_record["term"] = text
                    elif text in ["American", "International", "Other"]:
                        current_record["international"] = text
                    elif "GPA" in text:
                        current_record["gpa"] = text.replace("GPA", "").strip()
                    elif "GRE V" in text:
                        current_record["gre_verbal"] = text.replace("GRE V", "").strip()
                    elif "GRE AW" in text:
                        current_record["gre_aw"] = text.replace("GRE AW", "").strip()
                    elif "GRE" in text:
                        current_record["gre_quant"] = text.replace("GRE", "").strip()
                
                p_tag = row.find('p')
                if p_tag:
                    current_record["comments"] = p_tag.text.strip()
        
        if current_record:
            parsed_records.append(current_record)
            
    return parsed_records

def scrape_data(total_pages=2500):
    base_url = "https://www.thegradcafe.com/survey"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "raw_data.json")

    # Load existing data if it exists, or start fresh
    all_raw_data = [] 
    
    # We will use a counter to know when to save
    save_interval = 50 

    for page in range(1, total_pages + 1):
        print(f"Scraping page {page} of {total_pages}...")
        
        # [Driver initialization logic here...]
        
        try:
            # ... (Your current driver.get and parsing logic)
            all_raw_data.extend(page_data)
            
            # Incremental save
            if page % save_interval == 0:
                with open(file_path, "w", encoding="utf-8") as file:
                    json.dump(all_raw_data, file, indent=4)
                print(f"--- Saved progress up to page {page} ---")
            
        except Exception as e:
            print(f"Page {page} failed: {e}. Skipping to next...")
            continue # Don't break, just move on
            
    # Final save
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(all_raw_data, file, indent=4)
        
    print(f"Successfully saved {len(all_raw_data)} raw records to raw_data.json!")

if __name__ == "__main__":
    scrape_data(total_pages=2500)