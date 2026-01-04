# app/__init__.py
from flask import Flask, request
from .config import config
from .extensions import db, migrate, ma, jwt, bcrypt, socketio, init_cloudinary
from flask_restful import Api
from flask_cors import CORS
import os


def create_app(config_object=None):
    """Create and configure Flask application"""

    if config_object is None:
        env = os.getenv('FLASK_ENV', 'development')
        config_object = config.get(env, config['default'])

    app = Flask(__name__)
    app.config.from_object(config_object)

    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    instance_path = os.path.join(basedir, 'instance')
    os.makedirs(instance_path, exist_ok=True)

    upload_folder = app.config.get('UPLOAD_FOLDER')
    os.makedirs(upload_folder, exist_ok=True)

    # ========================
    # INITIALIZE EXTENSIONS
    # ========================
    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    socketio.init_app(app,
                      cors_allowed_origins="*",
                      async_mode='eventlet',
                      logger=True,
                      engineio_logger=False)

    # ⭐ CRITICAL: Create Api instance HERE
    api = Api(app)

    init_cloudinary(app)

    # ========================
    # IMPORT MODELS
    # ========================
    with app.app_context():
        from . import models
        print("✅ Models imported successfully")

    # ========================
    # CORS CONFIGURATION - FIXED FOR CREDENTIALS
    # ========================
    allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4200",
        "http://127.0.0.1:4200"
    ]

    CORS(app,
         resources={
             r"/api/*": {
                 "origins": allowed_origins,
                 "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                 "allow_headers": ["Content-Type", "Authorization", "Accept", "X-Requested-With"],
                 "expose_headers": ["Content-Type", "Authorization"],
                 "supports_credentials": True,
                 "max_age": 3600
             }
         },
         supports_credentials=True)

    print(f"✅ CORS enabled for: {', '.join(allowed_origins)}")

    # ========================
    # PREFLIGHT OPTIONS HANDLER - FIXED
    # ========================
    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            origin = request.headers.get('Origin')

            if origin not in allowed_origins:
                print(f"⚠️ Blocked origin: {origin}")
                return {"error": "Origin not allowed"}, 403

            response = app.make_default_options_response()
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Max-Age'] = '3600'
            return response

    # ========================
    # ADD CORS HEADERS TO ALL RESPONSES
    # ========================
    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get('Origin')
        if origin in allowed_origins:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Accept'
        return response

    # ========================
    # REGISTER API RESOURCES
    # ========================
    from .resources import register_resources
    register_resources(api)

    # ========================
    # HEALTH CHECK ENDPOINTS
    # ========================
    @app.route('/health')
    def health():
        return {
            'status': 'ok',
            'message': 'Backend is running',
            'database': 'connected',
            'cors': 'enabled',
            'version': '2.0.0'
        }, 200

    @app.route('/')
    def index():
        return {
            'message': 'TradeFlow Backend API',
            'version': '2.0.0',
            'status': 'running',
            'endpoints': {
                'health': '/health',
                'routes': '/api/routes',
                'auth_register': '/api/auth/register',
                'auth_login': '/api/auth/login',
                'strategies': '/api/strategies',
                'analyses': '/api/analyses',
                'trades': '/api/trades',
                'trade_logs': '/api/trade-logs',
                'trade_logs_stats': '/api/trade-logs/stats',
                'notifications': '/api/notifications'
            }
        }, 200

    # ========================
    # DEBUG: List all registered routes
    # ========================
    @app.route('/api/routes')
    def list_routes():
        """List all registered API routes"""
        routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static':
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': sorted(list(rule.methods - {'HEAD', 'OPTIONS'})),
                    'path': str(rule)
                })
        return {
            'total': len(routes),
            'routes': sorted(routes, key=lambda x: x['path'])
        }, 200

    # ========================
    # ERROR HANDLERS
    # ========================
    @app.errorhandler(413)
    def too_large(e):
        return {'error': 'File too large', 'message': 'Maximum file size is 16MB'}, 413

    @app.errorhandler(400)
    def bad_request(e):
        return {'error': 'Bad request',
                'message': str(e.description) if hasattr(e, 'description') else 'Invalid request'}, 400

    @app.errorhandler(404)
    def not_found(e):
        return {'error': 'Not found', 'message': 'The requested resource was not found'}, 404

    @app.errorhandler(500)
    def internal_error(e):
        return {'error': 'Internal server error', 'message': 'Something went wrong'}, 500

    # ========================
    # PRINT CONFIGURATION
    # ========================
    if app.debug:
        print("\n" + "=" * 70)
        print("🚀 TRADEFLOW BACKEND SERVER")
        print("=" * 70)
        print(f"🌍 Environment: {os.getenv('FLASK_ENV', 'development')}")
        print(f"🌐 Server: http://localhost:5000")
        print(f"🔗 API Base: http://localhost:5000/api")
        print(f"✅ CORS Origins: {', '.join(allowed_origins)}")
        print(f"☁️ Cloudinary: {app.config.get('CLOUDINARY_CLOUD_NAME', 'Not configured')}")
        print("-" * 70)
        print("📋 Key Endpoints:")
        print("   • GET  /health")
        print("   • GET  /api/routes")
        print("   • POST /api/auth/register")
        print("   • POST /api/auth/login")
        print("   • GET  /api/trade-logs/stats ⭐")
        print("   • GET  /api/trade-logs")
        print("   • GET  /api/notifications")
        print("=" * 70 + "\n")

    return app
