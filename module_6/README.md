# Grad Cafe Analytics Dashboard

An automated, test-driven ETL pipeline and web dashboard for analyzing graduate school admissions data. 

## Documentation
[**View the Full Sphinx Documentation on Read the Docs**](https://jhu-software-concepts-eddieperri.readthedocs.io)

## Fresh Installation & Reproducibility

To guarantee a clean environment that perfectly mirrors the development state, this project enforces strict dependency tracking. You can install the environment using either standard `pip` or the lightning-fast `uv` package manager.

### Option A: Standard pip Installation
1. Create a standard Python virtual environment:
   `python -m venv venv`
2. Activate the environment:
   - Windows: `venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
3. Install the frozen dependencies and the local package in editable mode:
   `pip install -r requirements.txt`
   `pip install -e .`

### Option B: High-Speed uv Installation
1. Create a virtual environment using uv:
   `uv venv`
2. Activate the environment (same as above).
3. Sync the exact environment state and install the local package:
   `uv pip sync requirements.txt`
   `uv pip install -e .`

## Database Configuration (Least Privilege)
This application enforces strict database security. It does not use the default PostgreSQL superuser.
Create a `.env` file in the root directory (use `.env.example` as a template) and provide your credentials:
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=thegradcafe
DB_USER=grad_app_user
DB_PASSWORD=your_secure_password


## Running the App
python src/flask_app.py
Navigate to http://127.0.0.1:5000/analysis in your browser.

## Pylint
To verify the linting score, from inside the module_5 folder, run:
pylint src/

## Snyk
We use `snyk test` to scan `requirements.txt` against vulnerability databases to ensure no compromised third-party libraries are introduced.
We could use `snyk code test` to scan our custom Python source code for insecure practices (like hardcoded secrets or SQL injection vulnerabilities). This code has not been tested using such a service.