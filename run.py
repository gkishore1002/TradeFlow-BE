import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Set Flask environment BEFORE importing app
os.environ.setdefault('FLASK_ENV', 'development')

from app import create_app

app = create_app()

if __name__ == '__main__':
    print(f"🚀 Starting Flask app...")
    print(f"📍 Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.run(debug=True, host='0.0.0.0', port=5000)
