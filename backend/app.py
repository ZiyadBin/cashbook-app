from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import datetime
import os
from sqlalchemy import func, distinct

from backend.config import Config
from backend.models import db, User, Transaction # Import db and new models
from backend.extensions import db, bcrypt # Import extensions
from backend.auth import authenticate_user

# --- App Initialization ---

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions with the app
db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)
CORS(app)

# --- Database Setup Helper ---
# This function will create your tables and your first user
# It runs once when the app starts.
@app.before_request
def setup_database():
    # Run this only once
    if not hasattr(app, 'database_initialized'):
        with app.app_context():
            db.create_all() # Create all tables
            
            # Check if default user exists
            user = User.query.filter_by(username="ZIYAD").first()
            if not user:
                # Create the user if they don't exist
                print("Creating default user ZIYAD...")
                default_user = User(username="ZIYAD")
                default_user.set_password("Admin123") # Hashes the password
                db.session.add(default_user)
                db.session.commit()
                print("Default user created.")
            
        app.database_initialized = True


# --- Helper Function to get Current User ---
def get_current_user_obj():
    """Helper function to get the full User object from the JWT identity."""
    username = get_jwt_identity()
    return User.query.filter_by(username=username).first()

# --- Authentication Routes ---

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        token = authenticate_user(username, password) # This now uses the DB
        if token:
            return jsonify({
                'message': 'Login successful',
                'access_token': token,
                'username': username
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Transaction Routes (Now using Database) ---

@app.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    try:
        current_user = get_current_user_obj()
        # Get transactions for this user, order by most recent
        user_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
        
        # Convert list of objects to list of dictionaries
        return jsonify({'transactions': [t.to_dict() for t in user_transactions]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['POST'])
@jwt_required()
def add_transaction():
    try:
        current_user = get_current_user_obj()
        data = request.get_json()
        
        if data.get('date'):
            try:
                transaction_date = datetime.fromisoformat(data['date'])
            except ValueError:
                transaction_date = datetime.utcnow()
        else:
            transaction_date = datetime.utcnow()
        
        # Create a new Transaction object
        new_transaction = Transaction(
            user_id=current_user.id,
            type=data['type'],
            amount=float(data['amount']),
            category=data['category'],
            remark=data.get('remark', ''),
            bank_cash=data['bank_cash'],
            date=transaction_date
        )
        
        # Add to the database session and commit
        db.session.add(new_transaction)
        db.session.commit()
        
        return jsonify({'message': 'Transaction added successfully', 'transaction': new_transaction.to_dict()}), 201
        
    except Exception as e:
        db.session.rollback() # Rollback in case of error
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
@jwt_required()
def update_transaction(transaction_id):
    try:
        current_user = get_current_user_obj()
        data = request.get_json()
        
        # Find the specific transaction in the DB
        transaction = Transaction.query.get(transaction_id)
        
        # Check if transaction exists and belongs to the user
        if not transaction or transaction.user_id != current_user.id:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Update fields
        if data.get('date'):
            try:
                transaction.date = datetime.fromisoformat(data['date'])
            except ValueError:
                pass # Keep existing date if parsing fails
        
        transaction.type = data['type']
        transaction.amount = float(data['amount'])
        transaction.category = data['category']
        transaction.remark = data.get('remark', '')
        transaction.bank_cash = data['bank_cash']
        
        db.session.commit() # Commit the changes
        
        return jsonify({'message': 'Transaction updated successfully', 'transaction': transaction.to_dict()}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    try:
        current_user = get_current_user_obj()
        
        transaction = Transaction.query.get(transaction_id)
        
        if not transaction or transaction.user_id != current_user.id:
            return jsonify({'error': 'Transaction not found'}), 404
        
        # Delete the transaction
        db.session.delete(transaction)
        db.session.commit()
        
        return jsonify({'message': 'Transaction deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- Summary & Analytics Routes (Now using Database) ---

@app.route('/api/summary', methods=['GET'])
@jwt_required()
def get_summary():
    try:
        current_user = get_current_user_obj()
        
        # Use SQLAlchemy to calculate sums
        cash_in = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='IN').scalar() or 0
        cash_out = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='OUT').scalar() or 0
        balance = cash_in - cash_out
        
        return jsonify({
            'cash_in': cash_in,
            'cash_out': cash_out,
            'balance': balance,
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard')
@jwt_required()
def get_dashboard():
    try:
        current_user = get_current_user_obj()
        
        # Start with a base query for the user
        query = Transaction.query.filter_by(user_id=current_user.id)
        
        # Get filters from query parameters
        type_filter = request.args.get('type', 'ALL')
        bank_filter = request.args.get('bank', 'ALL')
        
        # Apply filters
        if type_filter != 'ALL':
            query = query.filter_by(type=type_filter)
        if bank_filter != 'ALL':
            query = query.filter_by(bank_cash=bank_filter)
        
        # Execute the filtered query
        filtered_transactions = query.all()
        
        # Calculate summary
        cash_in = sum(t.amount for t in filtered_transactions if t.type == 'IN')
        cash_out = sum(t.amount for t in filtered_transactions if t.type == 'OUT')
        balance = cash_in - cash_out
        
        # Category breakdown
        category_breakdown = db.session.query(
            Transaction.category,
            Transaction.type,
            Transaction.bank_cash,
            func.sum(Transaction.amount)
        ).filter(Transaction.id.in_([t.id for t in filtered_transactions])) \
         .group_by(Transaction.category, Transaction.type, Transaction.bank_cash).all()
        
        # Bank breakdown
        bank_breakdown = db.session.query(
            Transaction.bank_cash,
            func.sum(Transaction.amount)
        ).filter(Transaction.id.in_([t.id for t in filtered_transactions])) \
         .group_by(Transaction.bank_cash).all()

        return jsonify({
            'summary': {
                'cash_in': cash_in,
                'cash_out': cash_out,
                'balance': balance
            },
            'category_breakdown': [
                {'category': c, 'type': t, 'bank_cash': b, 'amount': a}
                for c, t, b, a in category_breakdown
            ],
            'bank_breakdown': [
                {'bank_cash': k, 'amount': v} for k, v in bank_breakdown
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/banks')
@jwt_required()
def get_banks():
    try:
        current_user = get_current_user_obj()
        # Query for distinct bank_cash values for this user
        banks = db.session.query(distinct(Transaction.bank_cash)).filter_by(user_id=current_user.id).all()
        return jsonify([b[0] for b in banks]), 200 # un-tuple the results
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
@jwt_required()
def get_categories():
    try:
        current_user = get_current_user_obj()
        # Query for distinct category values for this user
        categories = db.session.query(distinct(Transaction.category)).filter_by(user_id=current_user.id).all()
        return jsonify([c[0] for c in categories]), 200 # un-tuple the results
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Serve Frontend (No changes here) ---

@app.route('/')
def serve_index():
    return send_from_directory('../frontend/pages', 'index.html')

@app.route('/login')
def serve_login():
    return send_from_directory('../frontend/pages', 'login.html')

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory('../frontend/pages', 'dashboard.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
