from flask import Flask
from .config import Config
from .extensions import db, migrate, ma, jwt, bcrypt
from .resources import register_resources
from flask_restful import Api
from flask_cors import CORS
import os

# Cloudinary
import cloudinary as cld

def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Cloudinary config: prefer environment variables
    cld.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True
    )

    # Ensure upload folder exists (kept for non-image assets if any)
    upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)
    print(f"Upload folder created/verified at: {upload_folder}")

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)

    # CORS for local frontend (adjust as needed)
    CORS(app,
         origins=["http://localhost:3000", "http://127.0.0.1:3000"],
         supports_credentials=True,
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
         allow_headers=["Content-Type", "Authorization", "Accept"],
         expose_headers=["Content-Type"])

    # Bind Flask-Restful API to app
    api = Api(app)
    register_resources(api)

    @app.route('/health')
    def health():
        return {
            'status': 'ok',
            'upload_folder': app.config.get('UPLOAD_FOLDER'),
            'max_content_length': app.config.get('MAX_CONTENT_LENGTH'),
            'environment': 'development' if app.debug else 'production'
        }, 200

    @app.route('/')
    def index():
        return {
            'message': 'Trading App Backend is running',
            'version': '1.0.0',
            'endpoints': {
                'health': '/health',
                'api': '/api/*',
                'files': '/api/files/*'
            }
        }, 200

    @app.errorhandler(413)
    def too_large(e):
        return {
            'error': 'File too large',
            'message': f'Maximum file size is {app.config.get("MAX_CONTENT_LENGTH", 16*1024*1024)} bytes'
        }, 413

    @app.errorhandler(400)
    def bad_request(e):
        return {
            'error': 'Bad request',
            'message': str(e.description) if hasattr(e, 'description') else 'Invalid request format'
        }, 400

    @app.errorhandler(500)
    def internal_error(e):
        return {
            'error': 'Internal server error',
            'message': 'Something went wrong on the server'
        }, 500

    if app.debug:
        print("🚀 Flask app created in DEBUG mode")
        print(f"📁 Upload folder: {upload_folder}")
        print(f"📊 Max file size: {app.config.get('MAX_CONTENT_LENGTH', 'Not set')}")
        print(f"🌐 CORS origins: http://localhost:3000")

    return app
