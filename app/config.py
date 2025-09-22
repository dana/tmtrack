import os

class Config:
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'tmtrack_db')
    MONGO_COLLECTION_NAME = os.environ.get('MONGO_COLLECTION_NAME', 'daily_tasks')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True') == 'True'
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
