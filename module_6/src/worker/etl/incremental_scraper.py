import urllib.parse
import time   # <---  Added to mimic human behavior and make sure scraping is polite
import random # <---  Added to mimic human behavior
import os     # <---  Lets code talk to window for important data
import json   # <--- Makes it easier to save files
import sys    # <--- Added for the graceful exit
from bs4 import BeautifulSoup  # <--- Good at reading messy html
from selenium import webdriver # <--- Actual robot that controls browser actions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



def initialize_driver():
    """Defines some Selenium settings that should help avoid bot detection"""
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")


    options.add_argument("--headless=new")          # Run invisibly
    options.add_argument("--no-sandbox")            # Bypass OS security
    options.add_argument("--disable-dev-shm-usage") # Overcome Docker memory limits
    
    
    return webdriver.Chrome(options=options)


def _parse_html_to_dicts(raw_html):
    """Private helper method to parse the GradCafe HTML into raw dictionaries."""
    soup = BeautifulSoup(raw_html, 'html.parser') # Makes the html easy to work with
    tbodies = soup.find_all('tbody')  # Pulls all the html t-bodies into a python list, which is the data we want
    parsed_records = []
    

    # Dig through each t-body in the tbodies list
    for tbody in tbodies:
        rows = tbody.find_all('tr', recursive=False)    # Stores all the rows that were inside the t-body as a list called 'rows' #recursive=false because we only need top-level rows 
        current_record = None
        

        # Dig through each row in the t-body
        for row in rows:
            classes = row.get('class', []) # Check the style of the row, and make an empty list (instead of crashing) if there is no class
            
            # Upper Row Student Data
            if 'tw-border-none' not in classes:  # If the row doesn't have no border (it has a border) then it must be the upper row of a student's data, if it is a student's data at all
                
                # If current_record has data in it, put it in the long-term storage (parsed_records) and clean current_record
                if current_record:
                    parsed_records.append(current_record)
                    current_record = None # The script will make some duplicate or incorrect data if we don't clean current_record here
                
                tds = row.find_all('td', recursive=False) # <td> is a vertical column cell in HTML. Grab every single cell in this row and line them up in the list variable 'tds'
                if len(tds) < 5: continue # if this row has less than 5 columns, it probably isn't a successfully loaded student dataset, and might crash our stuff, skip the rest of the 'if current_record' loop
                
                school = tds[0].text.strip() # grab the first [0] column in the row, use beautifulsoup's .text and python's native .strip to just get the text in there
                spans = tds[1].find_all('span') # grab the second column and chop it up into different spans as a list
                program = spans[0].text.strip() if len(spans) > 0 else "" # if spans contains something, the first value is 'program', otherwise, 'program' is a blank string
                degree = spans[1].text.strip() if len(spans) > 1 else "" # if the length of spans is greater than 1, get the text of the second span, otherwise just make 'degree' an empty string
                added_on = tds[2].text.strip() # the third column is the added date
                decision = tds[3].text.strip() # the fourth column is whether or not the person was accepted
                

                # Assembling the URL
                a_tag = row.find('a', href=True) #This line tells BeautifulSoup: "Look through this entire row and find an <a> tag, but only grab it if it actually has an href destination attached to it."
                url = "https://www.thegradcafe.com" + a_tag['href'] if a_tag else "" # This might leave room for going through the same page twice, but we will clean that up later
                
                current_record = {
                    "raw_program": f"{program}, {school}", # Since these are weirdly attached in the html, we put them together in our dictionary
                    "school": school,
                    "program": program,
                    "degree": degree,
                    "added_on": added_on,
                    "decision": decision,
                    "url": url,
                    "comments": "", # preparing these for the lower row of student data
                    "term": "",
                    "international": "",
                    "gpa": "",
                    "gre_quant": "",
                    "gre_verbal": "",
                    "gre_aw": ""
                }
            
            # Lower Row Student Data (Badges or Comments)
            else:
                if not current_record: continue # if there isn't any upper row data on current_record, skip this
                
                badges = row.find_all('div', class_='tw-inline-flex') # all these 'badges' are stored as a tw-inline-flex css class, all in the row go into the 'badges' list ("class_" has an underscore because python would be unhappy otherwise)
                for badge in badges:
                    text = badge.text.strip()       # all these badges appear to have very specific words in them; if this badge contains any of them, it is added to the appropriate place in 'current_record'
                    if any(term in text for term in ["Fall", "Spring", "Summer", "Winter"]):  # does the text contain any 'term' in the 'term' list?
                        current_record["term"] = text
                    elif text in ["American", "International", "Other"]:
                        current_record["international"] = text
                    elif "GPA" in text:
                        current_record["gpa"] = text.replace("GPA", "").strip() # cuts away 'GPA' letters from the actual GPA numbers
                    elif "GRE V" in text:
                        current_record["gre_verbal"] = text.replace("GRE V", "").strip()
                    elif "GRE AW" in text:
                        current_record["gre_aw"] = text.replace("GRE AW", "").strip()
                    elif "GRE" in text:
                        current_record["gre_quant"] = text.replace("GRE", "").strip()
                
                p_tag = row.find('p')   # finds the html <p> paragraph tag in the row, which will contain the comment
                if p_tag: # if there is something in the comment, put it in current_record
                    current_record["comments"] = p_tag.text.strip()
        
        if current_record: # if current_record was filled out, add it to the end of parsed_records
            parsed_records.append(current_record)
            
    return parsed_records # once it's all done, parsed_records becomes the final product of the function



def scrape_data(total_pages=2500):
    """Opens browser, types URLs, manages files, and stops when reaching known data."""

    base_url = "https://www.thegradcafe.com/survey"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "raw_data.json")

    # Resume Logic: Load existing data to check against
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            all_raw_data = json.load(file)
        print(f"Found existing file with {len(all_raw_data)} records.")
    else:
        all_raw_data = []

    # Create a set of URLs we already have. Sets are incredibly fast for "if x in set" lookups.
    existing_urls = {record["url"] for record in all_raw_data if record.get("url")}
    
    new_records_found = []
    overlap_found = False

    driver = initialize_driver()
    max_retries = 3 

    try:
        # ALWAYS start at page 1 to catch the newest submissions
        for page in range(1, total_pages + 1):
            print(f"Scraping page {page} for new data...")
            
            query_params = urllib.parse.urlencode({'page': page})
            target_url = f"{base_url}?{query_params}"
            
            # Retry Logic
            for attempt in range(max_retries):
                try:
                    driver.get(target_url)

                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "tbody"))
                    )
                    time.sleep(random.uniform(4.0, 7.5)) 
                    
                    page_data = _parse_html_to_dicts(driver.page_source)
                    
                    # --- NEW LOGIC: Check for Overlap ---
                    for record in page_data:
                        # If we hit a record we already have, we've reached the old data
                        if record["url"] and record["url"] in existing_urls:
                            overlap_found = True
                            break # Break out of the record loop
                        
                        # Otherwise, it's a brand new submission
                        new_records_found.append(record)
                    
                    # If successful, break out of the retry loop
                    break 

                except Exception as e:
                    print(f"  Attempt {attempt + 1} failed for page {page}: {e}")
                    if attempt < max_retries - 1:
                        print(f"  Retrying in 5 seconds...")
                        time.sleep(5)
                    else:
                        print(f"  Giving up on page {page} after {max_retries} attempts.")
            
            # If we found overlap on this page, stop scraping entirely
            if overlap_found:
                print(f"Reached existing data on page {page}. Stopping scrape.")
                break

    except KeyboardInterrupt:
        print("\n\nPause signal received! Saving current progress before exiting...")
    finally:
        driver.quit()
        
        # Add the new records to the TOP of the master list (so newest stays first)
        if new_records_found:
            all_raw_data = new_records_found + all_raw_data
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(all_raw_data, file, indent=4)
            print(f"Successfully pulled {len(new_records_found)} new records! Total is now {len(all_raw_data)}.")
        else:
            print("No new records found. Database is already up to date.")

if __name__ == "__main__":
    scrape_data(total_pages=2500)