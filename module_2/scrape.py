import urllib.parse
import time
import random
import os
import json
import sys  # <-- Added for the graceful exit
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

    # --- 1. RESUME LOGIC ---
    # Check if we already have data saved so we don't overwrite it
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            all_raw_data = json.load(file)
        print(f"Found existing file. Resuming with {len(all_raw_data)} records...")
    else:
        all_raw_data = []

    # Calculate starting page based on existing data (Assuming ~20 records per page)
    start_page = (len(all_raw_data) // 20) + 1 
    # -----------------------

    # Initialize driver ONCE
    driver = initialize_driver()
    save_interval = 50 
    max_retries = 3 

    # --- 2. GRACEFUL QUIT WRAPPER ---
    try:
        for page in range(start_page, total_pages + 1):
            print(f"Scraping page {page} of {total_pages}...")
            
            query_params = urllib.parse.urlencode({'page': page})
            target_url = f"{base_url}?{query_params}"
            
            # --- 3. RETRY LOGIC ---
            for attempt in range(max_retries):
                try:
                    driver.get(target_url)
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "tbody"))
                    )
                    time.sleep(random.uniform(4.0, 7.5)) 
                    
                    page_data = _parse_html_to_dicts(driver.page_source)
                    all_raw_data.extend(page_data)
                    
                    if page % save_interval == 0:
                        with open(file_path, "w", encoding="utf-8") as file:
                            json.dump(all_raw_data, file, indent=4)
                        print(f"--- Saved progress up to page {page} ---")
                    
                    # If successful, break out of the retry loop and move to the next page
                    break 
                    
                except Exception as e:
                    print(f"  Attempt {attempt + 1} failed for page {page}: {e}")
                    if attempt < max_retries - 1:
                        print(f"  Retrying in 5 seconds...")
                        time.sleep(5)
                    else:
                        print(f"  Giving up on page {page} after {max_retries} attempts. Skipping...")
            # ----------------------

    # Triggered if you press Ctrl+C in the terminal
    except KeyboardInterrupt:
        print("\n\nPause signal received! Saving current progress before exiting...")
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(all_raw_data, file, indent=4)
        print(f"Saved {len(all_raw_data)} records safely.")
        driver.quit()
        sys.exit(0)
    # --------------------------------

    # Final cleanup if the script runs all the way to 2,500
    driver.quit()
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(all_raw_data, file, indent=4)
        
    print(f"Successfully finished! Saved {len(all_raw_data)} raw records to raw_data.json.")

if __name__ == "__main__":
    scrape_data(total_pages=2500)