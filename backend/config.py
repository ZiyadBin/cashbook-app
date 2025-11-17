import os
from datetime import timedelta

class Config:
  SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-here')
  JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-dev-secret-here')
  JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
  JWT_TOKEN_LOCATION = ['headers']
  # ADD THESE TWO LINES:
  SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
  SQLALCHEMY_TRACK_MODIFICATIONS = False # Disables a warning
