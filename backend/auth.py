from flask_jwt_extended import create_access_token
from backend.models import User

def authenticate_user(username, password):
    """Authenticate user against the database and return JWT token"""
    
    # 1. Find the user in the database
    # .first() gets the user object or None if not found
    user = User.query.filter_by(username=username).first()
    
    # 2. Check if user exists and if the password is correct
    if user and user.check_password(password):
        # 3. Create a token with the username as the identity
        return create_access_token(identity=username)
        
    # 4. Return None if auth fails
    return None
