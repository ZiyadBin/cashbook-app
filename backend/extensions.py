from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

# Create the extension objects without an app
db = SQLAlchemy()
bcrypt = Bcrypt()
