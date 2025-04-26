from flask import Blueprint

# Create a blueprint for the API endpoints
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Import and register routes (order matters for conflicting routes)
from . import subscriptions
from . import ingestion
from . import status
