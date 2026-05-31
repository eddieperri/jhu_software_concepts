Eddie Perri
Module 2: Web Scraping, Due: 5/31/2026

Approach:
To solve this assignment, I separated the workflow into two distinct phases: Data Acquisition (scrape.py) and Data Processing/Standardization (clean.py).

Data Acquisition (scrape.py)
I used Selenium alongside BeautifulSoup to scrape applicant data from thegradcafe.com. Selenium allowed me to simulate a real browser environment, while BeautifulSoup efficiently parsed the nested <tbody> and <tr> HTML structures into Python dictionaries. 
To ensure the scraper was robust for a 2,500-page pull, I built a few safety mechanisms:
* I implemented a randomized 'time.sleep' interval between page fetches to respect server loads, adhering to best practices outlined in the site's robots.txt (which is within this folder labeled 'gradcaferobots.txt') and the assignment instructions. I also ran into some problems using a straight 2-second sleep (the website booted my bot) and this solved that issue.
* The script saves to 'raw_data.json' every 50 pages. I implemented logic to calculate the starting page based on the existing file length, allowing the scraper to resume after stopping without overwriting previous data. This works well, as long as there aren't too many new students posting, because they might cause duplicate data, but I do handle exact copies of the same piece of data in clean.py.
* I built an inner retry loop with a 15-second Selenium'WebDriverWait' that searches for the target CSS selector. If the page fails to load, it enters a 5-second cooldown and retries up to 3 times before skipping the page. This logic seems to work, but I did encounter some issues with it having skipped a lot of pages in a row.

Data Cleaning and LLM Standardization (clean.py)
Once the raw data was acquired, I processed it through `clean.py` to prepare it for the grading rubric.
* To optimize memory and speed for 50,000+ records, I implemented an O(n) single-pass deduplication algorithm. By converting each dictionary into an alphabetically sorted text string using `json.dumps(record, sort_keys=True)`, I created a hashable object to check against a `seen` set, instantly stripping thousands of exact duplicates.
* I mapped the raw HTML data into the specific key-value pairs required by the assignment rubric (e.g., mapping "decision" to "status", parsing the "added_on" string). I also preserved the original scraped string under the `raw_text_traceability` key.
* To standardize the university and program names, I triggered the local 1.1B parameter TinyLlama model via a Python `subprocess`. The cleaned data was passed via a temporary JSON file. I explicitly managed the threading to run sequentially rather than through a `ProcessPoolExecutor` to prevent the memory crashes associated with spawning multiple heavy LLM instances simultaneously. 
* The standardized data was streamed back from the LLM in JSON Lines format (.jsonl). I used a memory-efficient `for` loop to read the JSONL output line-by-line and format it back into a standard JSON array, saving the final product as `applicant_data.json`.