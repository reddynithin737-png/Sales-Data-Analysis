import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'sales-analysis-secret-key-2026')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'sales_db')
    
    # Database Type: 'sqlite' (primary) or 'mysql'
    DB_TYPE = os.getenv('DB_TYPE', 'sqlite')
    if os.getenv('VERCEL'):
        SQLITE_DB_PATH = '/tmp/sales_data.db'
        UPLOAD_FOLDER = '/tmp/uploads'
    else:
        SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sales_data.db')
        UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max
