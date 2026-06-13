Welcome to Grad Cafe Analytics' documentation!
==============================================

Overview & Setup
----------------
The Grad Cafe Analytics application is a data pipeline and web dashboard designed to scrape, clean, and display graduate school admission metrics.

**Local Setup Instructions:**

1. Clone the repository and navigate to the ``module_4`` directory.
2. Create and activate a virtual environment.
3. Install dependencies: ``pip install -r requirements.txt``
4. Create a ``.env`` file in the root directory containing your secure connection string:
   ``DATABASE_URL="postgresql://postgres:password@localhost:5432/thegradcafe"``
5. Run the web server: ``python src/flask_app.py``

Architecture
------------
The system is divided into three distinct layers:

* **Web Layer (Flask):** Serves the interactive HTML dashboard, handles background thread execution for long-running ETL processes, and manages the ``IS_SCRAPING`` concurrency lock to prevent data collision.
* **ETL Layer (Scripts):** Responsible for reaching out to the live Grad Cafe website, parsing raw HTML into standardized JSON, and sanitizing user inputs (e.g., enforcing GPA/GRE boundaries).
* **Database Layer (PostgreSQL):** An idempotent data store that uses unique constraints on applicant URLs to prevent duplicate entries. Calculates aggregations via raw SQL.

Testing Guide
-------------
The application utilizes Pytest with a strict 100% coverage policy.

**To run the test suite:**
Execute the following command in the terminal: ``pytest``

**Markers Used:**

* ``@pytest.mark.web``: Tests route availability and UI selector presence (e.g., ``data-testid="pull-data-btn"``).
* ``@pytest.mark.buttons``: Tests asynchronous API endpoints and 409 Conflict busy-gating.
* ``@pytest.mark.analysis``: Tests the two-decimal formatting constraint and "Answer:" labels.
* ``@pytest.mark.db``: Tests schema creation, constraint validation, and query dictionaries.
* ``@pytest.mark.integration``: Tests the full end-to-end ETL flow using faked scraper data.

**Key Fixtures:**

* ``test_db``: Intercepts the production database connection and routes it to a temporary, clean PostgreSQL schema that is torn down after the suite completes.
* ``client``: A Flask test client for simulating HTTP requests without running a live server.

API Reference
-------------
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`