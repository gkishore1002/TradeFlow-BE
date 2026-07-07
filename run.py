import os
import sys
from dotenv import load_dotenv

# Add current directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

from app import create_app
from app.extensions import socketio, db
from app.config import config

# Get current environment
env = os.getenv("FLASK_ENV", "development")

# Create Flask app
app = create_app(config[env])

# Initialize database
with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created/verified successfully")
    except Exception as e:
        print(f"⚠️ Database setup warning: {e}")

if __name__ == "__main__":

    # Render automatically provides the PORT environment variable.
    # Locally, it will default to 5000.
    port = int(os.environ.get("PORT", 5000))

    print("\n" + "=" * 70)
    print("🚀 TRADEFLOW BACKEND SERVER")
    print("=" * 70)
    print(f"🌍 Environment : {env}")
    print(f"🌐 Server      : http://0.0.0.0:{port}")
    print(f"🔗 API Base    : http://0.0.0.0:{port}/api")
    print(f"📊 Database    : {app.config.get('SQLALCHEMY_DATABASE_URI', 'Not Configured')}")
    print(f"☁️ Cloudinary  : {app.config.get('CLOUDINARY_CLOUD_NAME', 'Not Configured')}")
    print("=" * 70)

    try:
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=(env == "development"),
            allow_unsafe_werkzeug=True,
            use_reloader=False
        )

    except KeyboardInterrupt:
        print("\n👋 Server stopped gracefully.")

    except Exception as e:
        print(f"\n❌ Server Error: {e}")
        import traceback
        traceback.print_exc()