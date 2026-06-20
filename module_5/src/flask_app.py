import os
import sys
import subprocess
import threading
from flask import Flask, render_template, jsonify, request, redirect, url_for
from query_data import get_metrics  

def default_pipeline_runner(app_instance):
    """
    Executes the full Grad Cafe data pipeline: scraping, cleaning, and loading.

    This function runs as a background thread to prevent blocking the Flask application.
    It executes the scrape.py, clean.py, and load_data.py scripts sequentially
    using the subprocess module. It manages the IS_SCRAPING state flag to lock
    UI elements during execution.

    :param app_instance: The current Flask application instance containing the configuration.
    :type app_instance: flask.Flask
    :raises subprocess.CalledProcessError: If any of the underlying ETL scripts fail during execution.
    :raises Exception: For any other unhandled errors during pipeline execution.
    """
    app_instance.config['IS_SCRAPING'] = True
    
    # Get the absolute path of the directory containing THIS file (src)
    src_dir = os.path.dirname(os.path.abspath(__file__))
    
    scrape_script = os.path.join(src_dir, "web_scraping", "scrape.py")
    clean_script = os.path.join(src_dir, "web_scraping", "clean.py")
    load_script = os.path.join(src_dir, "load_data.py")
    
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
    """
    Flask application factory for the Grad Cafe Analytics system.

    Constructs and configures the Flask application, setting up database connections
    and registering routes. It supports dependency injection for testing purposes,
    allowing for mocked configurations and pipeline runners.

    :param test_config: Optional mapping of configuration values to override the defaults for testing.
    :type test_config: dict, optional
    :param pipeline_runner: Optional callable to override the default ETL pipeline execution. Used for injecting mocked runners during testing.
    :type pipeline_runner: callable, optional
    :returns: The configured Flask application instance ready to serve requests.
    :rtype: flask.Flask
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-key')
    
    # Default Configuration
    app.config['IS_SCRAPING'] = False
    app.config['DATABASE_URL'] = os.environ.get('DATABASE_URL', 'postgresql://localhost/grad_cafe')
    
    # Override config for tests if provided
    if test_config:
        app.config.update(test_config)

    # Dependency Injection: Use the provided fake runner for tests, or default to the real one
    runner = pipeline_runner or default_pipeline_runner

    @app.route('/')
    def home():
        """Redirects the root URL to the analysis dashboard."""
        return redirect(url_for('analysis'))

    @app.route('/analysis', methods=['GET'])
    def analysis():
        """
        Renders the main analysis dashboard.

        Retrieves the latest compiled metrics from the PostgreSQL database using
        the query_data module and injects them into the index.html template.

        :returns: Rendered HTML page displaying the Grad Cafe analysis metrics.
        :rtype: str
        """
        metrics = get_metrics()
        return render_template('index.html', metrics=metrics, is_scraping=app.config['IS_SCRAPING'])

    @app.route('/pull-data', methods=['POST'])
    def pull_data():
        """
        Endpoint to trigger the asynchronous ETL data pipeline.

        If a scraping process is not already active, this endpoint initiates the
        pipeline in a background thread and returns a 202 Accepted status. If a
        process is already running, it returns a 409 Conflict status.

        :returns: JSON response indicating success or busy state, along with the appropriate HTTP status code.
        :rtype: tuple
        """
        if app.config.get('IS_SCRAPING'):
            return jsonify({"busy": True}), 409
        
        # Run pipeline in background thread
        thread = threading.Thread(target=runner, args=(app,))
        thread.start()
        
        return jsonify({"ok": True}), 202
    
    @app.route('/status', methods=['GET'])
    def status():
        """Returns the current scraping state for the frontend polling."""
        return jsonify({"is_scraping": app.config.get('IS_SCRAPING', False)})
    
    @app.route('/update-analysis', methods=['POST'])
    def update_analysis():
        """
        Endpoint to verify if the application is ready to update the analysis display.

        Acts as a gating mechanism for the frontend. If the background scraper is
        currently running, it returns a 409 Conflict to prevent simultaneous database transactions.
        Otherwise, it returns a 200 OK.

        :returns: JSON response indicating readiness state, along with the appropriate HTTP status code.
        :rtype: tuple
        """
        if app.config.get('IS_SCRAPING'):
            return jsonify({"busy": True}), 409
            
        return jsonify({"ok": True}), 200

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)