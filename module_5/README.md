# Grad Cafe Analytics Dashboard

An automated, test-driven ETL pipeline and web dashboard for analyzing graduate school admissions data. 

## Documentation
[**View the Full Sphinx Documentation on Read the Docs**](https://jhu-software-concepts-eddieperri.readthedocs.io)

## Local Setup & Configuration

**1. Environment Setup**
Ensure you have Python 3.9+ and PostgreSQL installed.
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

**2. Database Configuration**
Create a .env file in the module_4 directory and provide your PostgreSQL credentials:
DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/thegradcafe"
SECRET_KEY="your_dev_secret_key"

**3. Run the app**
python src/flask_app.py
Navigate to http://127.0.0.1:5000/analysis in your browser.

**Running the tests**
This project enforces a 100% test coverage policy using Pytest, managed by a custom pytest.ini configuration.
Tests are fully isolated and use temporary database schemas via fixtures.


To run the full suite and generate a coverage report:

pytest -m "web or buttons or analysis or db or integration"