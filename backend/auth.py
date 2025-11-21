import requests
import os
from flask_jwt_extended import create_access_token
from extensions import db
from models import User

def authenticate_user(username, password):
    """
    Authenticates using a private JSON file from GitHub.
    Requires GITHUB_PAT and USERS_JSON_URL env variables.
    """
    try:
        # 1. Get secrets from Render Environment
        json_url = os.environ.get('USERS_JSON_URL')
        github_token = os.environ.get('GITHUB_PAT')

        if not json_url or not github_token:
            print("Error: USERS_JSON_URL or GITHUB_PAT not set in environment.")
            return None

        # 2. Fetch from GitHub with Authentication Header
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3.raw'
        }
        
        response = requests.get(json_url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error fetching users.json: Status {response.status_code}")
            return None
            
        users_list = response.json()
        
        # 3. Check credentials
        valid_user_data = None
        for u in users_list:
            # Case-insensitive username, sensitive password
            if u['username'].lower() == username.lower() and u['password'] == password:
                valid_user_data = u
                break
        
        if valid_user_data:
            # 4. Sync with Local Database (Required for transactions)
            local_user = User.query.filter_by(username=username).first()
            
            if not local_user:
                new_user = User(username=username)
                new_user.set_password("ManagedByPrivateJson") 
                db.session.add(new_user)
                db.session.commit()
            
            # 5. Return Token
            return create_access_token(identity=username)

    except Exception as e:
        print(f"Auth Error: {e}")
        return None

    return None
