# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
import cloudinary

# Initialize extensions WITHOUT app binding
db = SQLAlchemy()
migrate = Migrate()
ma = Marshmallow()
jwt = JWTManager()
bcrypt = Bcrypt()
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=True,
    engineio_logger=False
)

# ⚠️ NO Api() instance here anymore - created in __init__.py


def init_cloudinary(app):
    """Initialize Cloudinary with app config"""
    try:
        cloudinary.config(
            cloud_name=app.config.get('CLOUDINARY_CLOUD_NAME'),
            api_key=app.config.get('CLOUDINARY_API_KEY'),
            api_secret=app.config.get('CLOUDINARY_API_SECRET'),
            secure=True
        )
        if app.config.get('CLOUDINARY_CLOUD_NAME'):
            print(f"☁️ Cloudinary initialized: {app.config.get('CLOUDINARY_CLOUD_NAME')}")
        else:
            print("⚠️ Cloudinary not configured (using local storage)")
    except Exception as e:
        print(f"⚠️ Cloudinary initialization failed: {str(e)}")
