# Apologies for the excessive comments. I will try to be more concise in the future, 
# but I'm really trying to make sure everything makes sense in my own head


# Import the main Flask class to create our app, and render_template to load HTML files later
from flask import Flask, render_template

# Import the blueprint modules
from contact import contact_bp
from projects import projects_bp

# Initialize the Flask application
app = Flask(__name__)


# Register the blueprints with the main app
app.register_blueprint(contact_bp)
app.register_blueprint(projects_bp)


# The '@' symbol is a decorator. It tells Flask what URL should trigger the function below it.
# '/' represents the root directory, meaning this is the absolute homepage of your site.
@app.route('/')

def home():
    # When someone visits the homepage ('/'), this function runs and returns the rendered home.html template.
    
    return render_template('home.html')

# This standard Python conditional checks if you are running this script directly 
# (rather than importing it into another file). If so, it starts up the server.
if __name__ == '__main__':
    # Starts the Flask web server. 
    # host='0.0.0.0' tells the server to be accessible on all network interfaces.
    # port=8080 sets the specific port to listen on.
    # debug=True is a helpful developer tool that automatically restarts your server every time you save a file change, according to AI.
    app.run(host='0.0.0.0', port=8080, debug=True)