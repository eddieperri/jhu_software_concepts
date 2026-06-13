from flask import Flask, render_template, redirect, url_for, flash
import sys
import subprocess
import threading
import os
from query_data import get_metrics  # Importing your DRY database logic

app = Flask(__name__)
# Secret key is required for Flask 'flash' messages to work
app.secret_key = "jhu_super_secret_key" 

# --- STATE MANAGEMENT ---
# Global flag used to prevent the user from triggering multiple concurrent 
# scraping requests, which could break the code or just waste resources
is_scraping = False 

@app.route('/status')
def status():
    """API endpoint for frontend polling to monitor pipeline status."""
    global is_scraping
    return {'is_scraping': is_scraping}

def run_data_pipeline():
    """Runs the Scrape -> Clean -> Load pipeline with absolute paths."""
    global is_scraping
    is_scraping = True
    
    # Get the directory where app.py lives
    base_dir = os.getcwd() 
    
    # Build absolute paths to the scripts
    scrape_script = os.path.join(base_dir, "web_scraping", "scrape.py")
    clean_script = os.path.join(base_dir, "web_scraping", "clean.py")
    load_script = os.path.join(base_dir, "load_data.py")
    
    try:
        print(f"Starting pipeline...")

        # Execute pipeline stages sequentially.
        # check=True forces the process to raise an exception if a script fails.
        subprocess.run([sys.executable, scrape_script], check=True)
        
        print("Scraping complete. Cleaning data...")
        subprocess.run([sys.executable, clean_script], check=True)
        
        print("Cleaning complete. Loading to database...")
        subprocess.run([sys.executable, load_script], check=True)
        
        print("Pipeline fully complete!")
    except subprocess.CalledProcessError as e:
        print(f"Pipeline failed at a script execution step: {e}")
    except Exception as e:
        print(f"Pipeline failed: {e}")
    # Always release the button locks so the UI buttons become available again 
    finally:
        is_scraping = False

# --- FLASK ROUTES ---

@app.route('/')
def index():
    """Renders the dashboard with the latest analysis metrics."""
    metrics = get_metrics()
    return render_template('index.html', metrics=metrics, is_scraping=is_scraping)

@app.route('/pull_data', methods=['POST'])
def pull_data():
    """Triggered by the 'Pull Data' button, starting the scraper."""
    global is_scraping
    if is_scraping:
        flash("A data pull is already running in the background! Please wait for it to finish.", "warning")
    else:
        # Offload pipeline to a separate thread so the server remains responsive and the page doesn't freeze
        thread = threading.Thread(target=run_data_pipeline)
        thread.start()
        flash("Data pull initiated! The scraper is now running in the background. Check your VS Code terminal for live progress.", "success")
    
    return redirect(url_for('index'))

@app.route('/update_analysis', methods=['POST'])
def update_analysis():
    """Triggered by the 'Update Analysis' button, refreshes the dashboard metrics"""
    global is_scraping
    if is_scraping:
        flash("Cannot update analysis. The scraper is currently writing to the database. Please wait until it finishes.", "error")
    else:
        flash("Analysis updated successfully with the latest database records!", "success")
        
    # Redirecting to index automatically triggers get_metrics() again, refreshing the numbers
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)