"""
Main Flask application entry point and routing definitions.
"""
import os
from flask import Flask, render_template, jsonify, redirect, url_for

from publisher import publish_task
# pylint: disable=import-error
from worker.etl.query_data import get_metrics

def create_app(test_config=None):
    """Creates and configures the Flask application."""
    flask_app = Flask(__name__, template_folder='app/templates')
    flask_app.secret_key = os.environ.get('SECRET_KEY', 'dev-fallback-key')

    if test_config:
        flask_app.config.update(test_config)

    @flask_app.route('/')
    def home():
        return redirect(url_for('analysis'))

    @flask_app.route('/analysis', methods=['GET'])
    def analysis():
        metrics = get_metrics()
        return render_template('index.html', metrics=metrics)

    @flask_app.route('/pull-data', methods=['POST'])
    def pull_data():
        """Publishes a scrape task to RabbitMQ."""
        try:
            publish_task("scrape_new_data", payload={})
            return jsonify({"ok": True, "message": "Scrape task queued!"}), 202
        except Exception as e: # pylint: disable=broad-exception-caught
            return jsonify({"error": str(e)}), 503

    @flask_app.route('/update-analysis', methods=['POST'])
    def update_analysis():
        """Publishes an analytics recompute task to RabbitMQ."""
        try:
            publish_task("recompute_analytics", payload={})
            return jsonify({"ok": True, "message": "Analytics recompute queued!"}), 202
        except Exception as e: # pylint: disable=broad-exception-caught
            return jsonify({"error": str(e)}), 503

    @flask_app.route('/status', methods=['GET'])
    def status():
        """Returns a lightweight status object for frontend polling."""
        return jsonify({"is_scraping": False})

    return flask_app

if __name__ == '__main__':
    main_app = create_app()
    main_app.run(host='0.0.0.0', port=8080, debug=True)
