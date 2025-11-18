import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-here')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret-here')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ['headers']
    
    # Get the database URL
    db_url = os.environ.get('DATABASE_URL')
    
    # --- NEW AGGRESSIVE CHECK ---
    if not db_url:
        # If db_url is None OR an empty string, raise an error
        raise ValueError("FATAL ERROR: DATABASE_URL is not set in Render environment. Please add it and save changes.")
    
    if db_url.startswith("postgres://"):
        # This is the correct path, modify it for the new driver
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
