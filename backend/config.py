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
    
    # Check if it starts with the expected string
    if db_url.startswith("postgres://"):
        print("+++ URL starts with 'postgres://'. Modifying for psycopg. +++")
        db_url = db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif db_url.startswith("postgresql://"):
        # --- NEW CATCH ---
        # What if it already starts with 'postgresql://'?
        print("+++ URL starts with 'postgresql://'. Modifying for psycopg. +++")
        db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    else:
        print(f"!!!! WARNING: DATABASE_URL ('{db_url}') does not start with 'postgres://' or 'postgresql://'. App will likely fail. !!!!")

    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
