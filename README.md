🚀 QUICK START GUIDE - TRADEFLOW

1. Prerequisites

- Python 3.8+ installed
- Node.js 18+ installed
- Git installed

STEP 1: Clone the Repository

- git clone https://github.com/your-username/tradeflow.git
- cd tradeflow

STEP 2: Setup BACKEND

2.1 Navigate to Project Folder

- cd project_folder_name

2.2 Create Virtual Environment

- python -m venv venv
- venv\Scripts\activate

2.3 Install Dependencies

- pip install -r requirements.txt

2.4 Create .env File

- Add the .env content

2.5 Setup Database - Run this command 

- python -c "from app import create_app; app = create_app(); app.app_context().push(); from app.extensions import db; db.create_all(); print('✅ SQLite Database initialized!')"

2.6 Run Backend Server

- python run.py







