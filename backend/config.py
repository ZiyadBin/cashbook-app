import os
from datetime import timedelta

class Config:
    # These lines must be indented
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-here')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret-here')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ['headers']
    
    # Get the database URL from Render
    db_url = os.environ.get('DATABASE_URL')
    
    # Tell SQLAlchemy to use the new 'psycopg' (v3) driver
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    
    # These lines must also be indented
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Disables a warning
