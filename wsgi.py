from flask import Flask
from flask_cors import CORS # Import CORS
from webhook_service.config import Config
from webhook_service.database import db_session, init_db, shutdown_session
from webhook_service.api import api_bp

app = Flask(__name__)

app.config.from_object(Config)

# Enable CORS for routes under the '/api' blueprint
# This allows requests from any origin (*) to your API endpoints.
# For production, you should restrict 'origins' to specific domains.
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.register_blueprint(api_bp, url_prefix='/api')

# Register the database session teardown function
app.teardown_appcontext(shutdown_session)

@app.route('/')
def index():
    return "Webhook Service is running!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
