Eddie Perri
Module 2: Web Scraping, Due: 5/31/2026

Approach:
To solve this assignment, I separated the workflow into two distinct phases: Data Acquisition (scrape.py) and Data Processing/Standardization (clean.py).

Data Acquisition (scrape.py)
I used Selenium (with Chrome) alongside BeautifulSoup and urllib to scrape applicant data from thegradcafe.com. Selenium allowed me to simulate a real browser environment, while BeautifulSoup efficiently parsed the nested <tbody> and <tr> HTML structures into Python dictionaries. 
To ensure the scraper was robust enough for a 2,500-page pull, I built a few safety mechanisms:
* I implemented a randomized 'time.sleep' interval between page fetches to respect server loads, despite the relatively unclear nature of the site's robots.txt (which is saved within this folder labeled 'gradcaferobots.txt' along side a screenshot of the robots.txt in the browser). I ran into some problems using a straight 2-second sleep (the website booted my bot) and this solved that issue.
* The script saves to 'raw_data.json' every 50 pages. I implemented logic to calculate the starting page based on the existing file length, allowing the scraper to resume after stopping without overwriting previous data. This works well, as long as there aren't too many new students posting, because they might cause duplicate data, but I do handle exact copies of the same piece of data in clean.py.
* I built an inner retry loop with a 15-second Selenium'WebDriverWait' that searches for the target CSS selector. If the page fails to load, it enters a 5-second cooldown and retries up to 3 times before skipping the page. This logic seems to work, but I did encounter some issues with it having skipped a lot of pages in a row.

Data Cleaning and LLM Standardization (clean.py)
Once I had the raw data, I processed it through 'clean.py'.
* I added a deduplication algorithm by converting each dictionary into an alphabetically sorted text string using 'json.dumps(record, sort_keys=True)', and checked against a 'seen' set.
* I took the raw website data and renamed the data labels to match the proper format (for example, changing the label 'decision' to 'status' and cleaning up the date format).
* To standardize the university and program names, I triggered the local 1.1B parameter TinyLlama model via a Python subprocess. The cleaned data was passed via a temporary JSON file. I tried changing the threading to run sequentially rather than through a `ProcessPoolExecutor` to prevent the memory crashes associated with spawning multiple heavy LLM instances simultaneously, but had some issues, so I changed it back. The llm processing seems to still be rather slow at this time. 
* The standardized data was streamed back from the LLM in JSON Lines format (.jsonl). I used a loop to read the JSONL output line-by-line and format it back into a standard JSON array, saving the final product as 'applicant_data.json'.