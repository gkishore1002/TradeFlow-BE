# extensions.py - UPDATED
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from flask_restful import Api
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
import cloudinary

db = SQLAlchemy()
migrate = Migrate()
ma = Marshmallow()
api = Api()
jwt = JWTManager()
bcrypt = Bcrypt()

def init_cloudinary(app):
    cloudinary.config(
        cloud_name=app.config.get('CLOUDINARY_CLOUD_NAME'),
        api_key=app.config.get('CLOUDINARY_API_KEY'),
        api_secret=app.config.get('CLOUDINARY_API_SECRET')
    )
