from app import create_app
from app.extensions import db
from app.config import config
import os

app = create_app(config[os.getenv('FLASK_ENV') or 'default'])


@app.cli.command('create-db')
def create_db():
    """Create database tables."""
    with app.app_context():
        # Models are already imported in create_app(), so just create tables
        db.create_all()
        print(f'✅ Database tables created at: {app.config["SQLALCHEMY_DATABASE_URI"]}')

        # Verify tables were created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f'📊 Tables: {", ".join(tables) if tables else "None"}')


if __name__ == '__main__':
    app.cli()
