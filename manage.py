from app import create_app
from app.extensions import db
app = create_app()
@app.cli.command('create-db')
def create_db():
    with app.app_context():
        db.create_all()
        print('Database tables created.')
