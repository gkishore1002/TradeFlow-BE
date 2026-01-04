# run.py
import os
import sys
from dotenv import load_dotenv

# Add current directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

# Set Flask environment
os.environ.setdefault('FLASK_ENV', 'development')

from app import create_app
from app.extensions import socketio, db
from app.config import config

# Get environment and create app
env = os.getenv('FLASK_ENV', 'development')
app = create_app(config[env])

# Initialize database
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created/verified successfully")
    except Exception as e:
        print(f"⚠️ Database setup warning: {str(e)}")

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("🚀 TRADEFLOW BACKEND SERVER - STARTING...")
    print("=" * 70)
    print(f"🌍 Environment: {env}")
    print(f"🌐 Backend URL: http://localhost:5000")
    print(f"🔗 API Base: http://localhost:5000/api")
    print(f"✅ Frontend CORS: http://localhost:3000")
    print(f"📡 WebSocket: ws://localhost:5000/socket.io/")
    print(f"📊 Database: {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not configured')}")
    print(f"☁️ Cloudinary: {app.config.get('CLOUDINARY_CLOUD_NAME', 'Not configured')}")
    print("=" * 70)
    print("⚠️  IMPORTANT: Keep this terminal running!")
    print("=" * 70 + "\n")

    try:
        socketio.run(
            app,
            host='0.0.0.0',
            port=5000,
            debug=True,
            allow_unsafe_werkzeug=True,
            use_reloader=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped gracefully\n")
    except Exception as e:
        print(f"\n❌ Server error: {str(e)}\n")
        import traceback

        traceback.print_exc()
