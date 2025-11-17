from datetime import datetime
from extensions import db, bcrypt

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    
    # This creates a 'user.transactions' list on a user object
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        """Hashes and sets the password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        """Checks a password against the hash."""
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(10), nullable=False) # 'IN' or 'OUT'
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    remark = db.Column(db.String(200), nullable=True)
    bank_cash = db.Column(db.String(100), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Foreign Key to link to the User table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def to_dict(self):
        """Converts the transaction to a dictionary."""
        return {
            'transaction_id': self.id, # Use the database ID
            'user_id': self.user_id,
            'type': self.type,
            'amount': self.amount,
            'category': self.category,
            'remark': self.remark,
            'bank_cash': self.bank_cash,
            'date': self.date.isoformat()
        }

    def __repr__(self):
        return f'<Transaction {self.id} - {self.type} - {self.amount}>'
