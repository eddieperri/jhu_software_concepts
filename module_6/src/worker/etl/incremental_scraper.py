"""Incremental scraper for TheGradCafe.

Contains functions to initialize a Selenium driver, parse HTML pages into
record dictionaries and to iterate pages until previously-seen data is
encountered.

The HTML parsing logic is intentionally imperative; many local variables
are used while extracting fields. Pylint complexity limits are disabled
at module level to avoid large refactors here.
"""

# pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks,broad-exception-caught,too-many-statements

import urllib.parse
import time
import random
import os
import json
# `sys` is not needed in this module
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



def initialize_driver():
    """Create and return a headless Chrome webdriver with basic options."""
    options = webdriver.ChromeOptions()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(options=options) # pylint: disable=not-callable


def _parse_html_to_dicts(raw_html):
    """Parse GradCafe HTML and return a list of record dictionaries."""
    soup = BeautifulSoup(raw_html, "html.parser")
    tbodies = soup.find_all("tbody")
    parsed_records = []

    for tbody in tbodies:
        rows = tbody.find_all("tr", recursive=False)
        current_record = {}
        in_record = False

        for row in rows:
            classes = row.get("class", [])

            # Upper Row Student Data
            if "tw-border-none" not in classes:
                if in_record:
                    parsed_records.append(current_record.copy())
                    current_record.clear()
                    in_record = False

                tds = row.find_all("td", recursive=False)
                if len(tds) < 5:
                    continue

                school = tds[0].text.strip()
                spans = tds[1].find_all("span")
                program = spans[0].text.strip() if len(spans) > 0 else ""
                degree = spans[1].text.strip() if len(spans) > 1 else ""
                added_on = tds[2].text.strip()
                decision = tds[3].text.strip()

                a_tag = row.find("a", href=True)
                url = "https://www.thegradcafe.com" + a_tag["href"] if a_tag else ""

                current_record = {
                    "raw_program": f"{program}, {school}",
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
                    "gre_aw": "",
                }
            else:
                if not in_record:
                    continue

                badges = row.find_all("div", class_="tw-inline-flex")
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

                p_tag = row.find("p")
                if p_tag:
                    current_record["comments"] = p_tag.text.strip()

        if in_record:
            parsed_records.append(current_record.copy())

    return parsed_records



def scrape_data(total_pages=2500):
    """Open the browser and iterate pages until overlap with existing data."""

    base_url = "https://www.thegradcafe.com/survey"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "raw_data.json")

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            all_raw_data = json.load(file)
        print(f"Found existing file with {len(all_raw_data)} records.")
    else:
        all_raw_data = []

    existing_urls = {record["url"] for record in all_raw_data if record.get("url")}

    new_records_found = []
    overlap_found = False

    driver = initialize_driver()
    max_retries = 3

    try:
        for page in range(1, total_pages + 1):
            print(f"Scraping page {page} for new data...")

            query_params = urllib.parse.urlencode({"page": page})
            target_url = f"{base_url}?{query_params}"

            for attempt in range(max_retries):
                try:
                    driver.get(target_url)

                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "tbody"))
                    )
                    time.sleep(random.uniform(4.0, 7.5))

                    page_data = _parse_html_to_dicts(driver.page_source)

                    for record in page_data:
                        if record.get("url") and record["url"] in existing_urls:
                            overlap_found = True
                            break

                        new_records_found.append(record)

                    break

                except Exception as exc:  # pragma: no cover - network/driver instability
                    print(f"  Attempt {attempt + 1} failed for page {page}: {exc}")
                    if attempt < max_retries - 1:
                        print("  Retrying in 5 seconds...")
                        time.sleep(5)
                    else:
                        print(f"  Giving up on page {page} after {max_retries} attempts.")

            if overlap_found:
                print(f"Reached existing data on page {page}. Stopping scrape.")
                break

    except KeyboardInterrupt:
        print("\n\nPause signal received! Saving current progress before exiting...")
    finally:
        driver.quit()

        if new_records_found:
            all_raw_data = new_records_found + all_raw_data
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(all_raw_data, file, indent=4)
            print(f"Successfully pulled {len(new_records_found)} new records!")
            print(f"Total is now {len(all_raw_data)}.")
        else:
            print("No new records found. Database is already up to date.")

if __name__ == "__main__":
    scrape_data(total_pages=2500)
