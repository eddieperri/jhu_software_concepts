You must have PostgreSQL downloaded in order to run this software. I downloaded it from here: https://www.postgresql.org/download/



# Module 3: GradCafe Analysis Pipeline

This repository contains an end-to-end data pipeline to scrape, clean, standardize (via local LLM), store, and visualize admissions data from The GradCafe.

## Setup Instructions

1. **Environment Setup:**
   - Create a virtual environment if you wish: `python -m venv venv`
   - Activate it: `source venv/bin/activate` (or `.\venv\Scripts\activate` on Windows)
   - Install dependencies: `pip install -r requirements.txt`

2. **Database Setup:**
   - Ensure PostgreSQL is running.
   - Create a database named `thegradcafe`.
   - Run the provided schema.sql file to create the table
   - Create a `.env` file in the root folder with your database password: `DB_PASSWORD=your_password_here`

3. **Running the Application:**
   - Start the Flask web server: `python app.py`
   - Open your browser to `http://127.0.0.1:5000`

## Project Components
- `scrape.py` and `clean.py`: Handles incremental web scraping and LLM standardization.
- `load_data.py`: Migrates cleaned JSON data into PostgreSQL.
- `query_data.py`: Contains the analytical SQL logic.
- `app.py`: Flask controller that manages the web dashboard and triggers background pipelines.