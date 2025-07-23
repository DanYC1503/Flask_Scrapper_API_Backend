from flask import Flask
from app.API_Gateways.api_routes import api_bp
from app.config import Config
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    # Register the blueprint
    app.register_blueprint(api_bp)
    CORS(app)
    
    return app
