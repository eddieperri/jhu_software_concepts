import os
import sys
import subprocess
import threading
from flask import Flask, render_template, jsonify, request
from query_data import get_metrics  # Importing your DRY database logic

def default_pipeline_runner(app_instance):
    """The real ETL pipeline using absolute paths and subprocesses."""
    app_instance.config['IS_SCRAPING'] = True
    base_dir = os.getcwd() 
    
    scrape_script = os.path.join(base_dir, "src", "web_scraping", "scrape.py")
    clean_script = os.path.join(base_dir, "src", "web_scraping", "clean.py")
    load_script = os.path.join(base_dir, "src", "load_data.py")
    
    try:
        print("Starting pipeline...")
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
    finally:
        # Always release the lock
        app_instance.config['IS_SCRAPING'] = False

def create_app(test_config=None, pipeline_runner=None):
    """Flask application factory."""
    app = Flask(__name__)
    app.secret_key = "jhu_super_secret_key"
    
    # Default Configuration
    app.config['IS_SCRAPING'] = False
    app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/grad_cafe')
    
    # Override config for tests if provided
    if test_config:
        app.config.update(test_config)

    # Dependency Injection: Use the provided fake runner for tests, or default to the real one
    runner = pipeline_runner or default_pipeline_runner

    @app.route('/analysis', methods=['GET'])
    def analysis():
        """Renders the dashboard. Rubric requires GET /analysis"""
        metrics = get_metrics()
        return render_template('index.html', metrics=metrics, is_scraping=app.config['IS_SCRAPING'])

    @app.route('/pull-data', methods=['POST'])
    def pull_data():
        """Triggered by the 'Pull Data' button. Rubric requires POST /pull-data"""
        if app.config.get('IS_SCRAPING'):
            # Rubric: Return 409 with {"busy": true} when a pull is in progress
            return jsonify({"busy": True}), 409
        
        # Run pipeline in background thread
        thread = threading.Thread(target=runner, args=(app,))
        thread.start()
        
        # Rubric: Return 202 with {"ok": true} when starting
        return jsonify({"ok": True}), 202

    @app.route('/update-analysis', methods=['POST'])
    def update_analysis():
        """Triggered by the 'Update Analysis' button. Rubric requires POST /update-analysis"""
        if app.config.get('IS_SCRAPING'):
            # Rubric: Return 409 with {"busy": true} when a pull is in progress
            return jsonify({"busy": True}), 409
            
        # Rubric: Returns 200 when not busy
        return jsonify({"ok": True}), 200

    return app

if __name__ == '__main__':
    # When running normally, spin up the app using the factory
    app = create_app()
    app.run(debug=True)