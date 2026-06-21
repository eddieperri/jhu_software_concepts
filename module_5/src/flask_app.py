"""
Main Flask application entry point and routing definitions for the Grad Cafe Analytics system.
"""
import os
import sys
import subprocess
import threading
from flask import Flask, render_template, jsonify, redirect, url_for
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
    :raises subprocess.CalledProcessError: If any of the underlying ETL scripts fail.
    """
    app_instance.config['IS_SCRAPING'] = True

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
    except RuntimeError as e:
        print(f"Pipeline failed: {e}")
    finally:
        app_instance.config['IS_SCRAPING'] = False

def create_app(test_config=None, pipeline_runner=None):
    """
    Flask application factory for the Grad Cafe Analytics system.
    """
    flask_app = Flask(__name__)
    flask_app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-key')

    flask_app.config['IS_SCRAPING'] = False
    flask_app.config['DATABASE_URL'] = os.environ.get(
        'DATABASE_URL', 'postgresql://localhost/grad_cafe'
    )

    if test_config:
        flask_app.config.update(test_config)

    runner = pipeline_runner or default_pipeline_runner

    @flask_app.route('/')
    def home():
        """Redirects the root URL to the analysis dashboard."""
        return redirect(url_for('analysis'))

    @flask_app.route('/analysis', methods=['GET'])
    def analysis():
        """Renders the main analysis dashboard."""
        metrics = get_metrics()
        return render_template(
            'index.html',
            metrics=metrics,
            is_scraping=flask_app.config['IS_SCRAPING']
        )

    @flask_app.route('/pull-data', methods=['POST'])
    def pull_data():
        """Endpoint to trigger the asynchronous ETL data pipeline."""
        if flask_app.config.get('IS_SCRAPING'):
            return jsonify({"busy": True}), 409

        thread = threading.Thread(target=runner, args=(flask_app,))
        thread.start()

        return jsonify({"ok": True}), 202

    @flask_app.route('/status', methods=['GET'])
    def status():
        """Returns the current scraping state for the frontend polling."""
        return jsonify({"is_scraping": flask_app.config.get('IS_SCRAPING', False)})

    @flask_app.route('/update-analysis', methods=['POST'])
    def update_analysis():
        """Endpoint to verify if the application is ready to update the analysis display."""
        if flask_app.config.get('IS_SCRAPING'):
            return jsonify({"busy": True}), 409

        return jsonify({"ok": True}), 200

    return flask_app

if __name__ == '__main__':
    main_app = create_app()
    main_app.run(debug=True)
