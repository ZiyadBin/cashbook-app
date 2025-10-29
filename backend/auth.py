#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from flask_jwt_extended import create_access_token
from models import users_db

def authenticate_user(username, password):
    """Authenticate user and return JWT token"""
    user = users_db.get(username)
    if user and user['password'] == password:
        return create_access_token(identity=username)
    return None

