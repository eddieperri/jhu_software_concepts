from flask import Blueprint, render_template

# Create the Blueprint object for projects
projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/projects')
def projects_page():
    return render_template('projects.html')