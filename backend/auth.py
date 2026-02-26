from models import User
from flask_jwt_extended import create_access_token

def authenticate_user(username, password):
    """
    Authenticates directly against the Neon PostgreSQL Database.
    No more GitHub tokens required!
    """
    try:
        # 1. Look up the user in the database (case-insensitive)
        user = User.query.filter(User.username.ilike(username)).first()
        
        # 2. Check if the user exists and the password matches
        if user and user.check_password(password):
            
            # 3. Create and return the login token
            # We use user.username to ensure the exact capitalization from the DB is used
            return create_access_token(identity=user.username)
            
        # Return None if login fails
        return None
        
    except Exception as e:
        print(f"Auth Error: {e}")
        return None
