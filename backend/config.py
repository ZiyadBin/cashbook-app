import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-here')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret-here')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    JWT_TOKEN_LOCATION = ['headers']
    
    # Get the database URL from Render
    db_url = os.environ.get('DATABASE_URL')
    
    # --- NEW DEBUGGING CODE ---
    if db_url is None:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!!! FATAL ERROR: DATABASE_URL environment variable is NOT SET. !!!!")
        print("!!!! Please add it in the Render dashboard. !!!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    elif db_url.startswith("postgres://"):
        # This is the correct path:
        print("+++ DATABASE_URL found. Applying psycopg driver. +++")
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
