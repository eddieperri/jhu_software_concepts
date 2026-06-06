from flask import Flask, render_template, redirect, url_for, flash
import sys
import subprocess
import threading
from query_data import get_metrics  # Importing your DRY database logic

app = Flask(__name__)
# Secret key is required for Flask 'flash' messages to work
app.secret_key = "jhu_super_secret_key" 

# --- STATE MANAGEMENT ---
# This global variable tracks if the background scraper is currently running
is_scraping = False 

@app.route('/status')
def status():
    global is_scraping
    return {'is_scraping': is_scraping}

def run_data_pipeline():
    """Runs the Scrape -> Clean -> Load pipeline in the background."""
    global is_scraping
    is_scraping = True
    try:
        print("Starting background pipeline: Scraping...")
        # Pointing directly to your scripts inside the web_scraping folder
        subprocess.run([sys.executable, "web_scraping/scrape.py"], check=True)
        
        print("Scraping complete. Cleaning data...")
        subprocess.run([sys.executable, "web_scraping/clean.py"], check=True)
        
        print("Cleaning complete. Loading to database...")
        subprocess.run([sys.executable, "load_data.py"], check=True)
        
        print("Pipeline fully complete!")
    except subprocess.CalledProcessError as e:
        print(f"Pipeline failed at a script execution step: {e}")
    except Exception as e:
        print(f"Pipeline failed: {e}")
    finally:
        # Ensures the lock is lifted even if the script crashes
        is_scraping = False

# --- FLASK ROUTES ---

@app.route('/')
def index():
    """Fetches the latest metrics and renders the dashboard."""
    # Call your imported function to grab the live SQL data dictionary
    metrics = get_metrics()
    return render_template('index.html', metrics=metrics, is_scraping=is_scraping)

@app.route('/pull_data', methods=['POST'])
def pull_data():
    """Triggered by the 'Pull Data' button."""
    global is_scraping
    if is_scraping:
        flash("A data pull is already running in the background! Please wait for it to finish.", "warning")
    else:
        # Start the pipeline in a background thread so the webpage doesn't freeze
        thread = threading.Thread(target=run_data_pipeline)
        thread.start()
        flash("Data pull initiated! The scraper is now running in the background. Check your VS Code terminal for live progress.", "success")
    
    return redirect(url_for('index'))

@app.route('/update_analysis', methods=['POST'])
def update_analysis():
    """Triggered by the 'Update Analysis' button."""
    global is_scraping
    if is_scraping:
        flash("Cannot update analysis. The scraper is currently writing to the database. Please wait until it finishes.", "error")
    else:
        flash("Analysis updated successfully with the latest database records!", "success")
        
    # Redirecting to index automatically triggers get_metrics() again, refreshing the numbers
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)