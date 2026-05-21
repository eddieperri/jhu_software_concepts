# Apologies for the excessive comments. I will try to be more concise in the future, 
# but I'm really trying to make sure everything makes sense in my own head on my first go around


# Import the main Flask class to create our app, and render_template to load HTML files later
from flask import Flask, render_template

# Import the blueprint modules
from routes.contact import contact_bp
from routes.projects import projects_bp

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



if __name__ == '__main__':
    # Starts the Flask web server. 
    # host='0.0.0.0' tells the server to be accessible on all network interfaces.
    # port=8080 sets the specific port to listen on.
    # debug=True is a helpful developer tool that automatically restarts your server every time you save a file change, but is also a security risk.

    #app.run(host='0.0.0.0', port=8080, debug=True)
    # Above is what it looks like when you are safe to run the application in a development environment.

    app.run(host='0.0.0.0', port=8080)