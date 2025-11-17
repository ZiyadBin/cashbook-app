from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
import uuid
from datetime import datetime
import os

from config import Config
from models import users_db, transactions_db, Transaction
from auth import authenticate_user

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
jwt = JWTManager(app)

# Authentication routes
@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        token = authenticate_user(username, password)
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

# Transaction routes
@app.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    try:
        current_user = get_jwt_identity()
        user_transactions = [t.to_dict() for t in transactions_db if t.user_id == current_user]
        return jsonify({'transactions': user_transactions}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['POST'])
@jwt_required()
def add_transaction():
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        
        # Parse date or use current time
        if data.get('date'):
            try:
                # Handle datetime-local format (YYYY-MM-DDTHH:MM)
                transaction_date = datetime.fromisoformat(data['date'])
            except ValueError:
                # Fallback to current time if parsing fails
                transaction_date = datetime.utcnow()
        else:
            transaction_date = datetime.utcnow()
        
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            user_id=current_user,
            type=data['type'],
            amount=float(data['amount']),
            category=data['category'],
            remark=data.get('remark', ''),
            bank_cash=data['bank_cash'],
            date=transaction_date
        )
        
        transactions_db.append(transaction)
        return jsonify({'message': 'Transaction added successfully', 'transaction': transaction.to_dict()}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<transaction_id>', methods=['PUT'])
@jwt_required()
def update_transaction(transaction_id):
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        
        for transaction in transactions_db:
            if transaction.transaction_id == transaction_id and transaction.user_id == current_user:
                # Parse date or keep existing
                if data.get('date'):
                    try:
                        transaction.date = datetime.fromisoformat(data['date'])
                    except ValueError:
                        # Keep existing date if parsing fails
                        pass
                
                transaction.type = data['type']
                transaction.amount = float(data['amount'])
                transaction.category = data['category']
                transaction.remark = data.get('remark', '')
                transaction.bank_cash = data['bank_cash']
                
                return jsonify({'message': 'Transaction updated successfully', 'transaction': transaction.to_dict()}), 200
        
        return jsonify({'error': 'Transaction not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<transaction_id>', methods=['DELETE'])
@jwt_required()
def delete_transaction(transaction_id):
    try:
        current_user = get_jwt_identity()
        global transactions_db
        
        for i, transaction in enumerate(transactions_db):
            if transaction.transaction_id == transaction_id and transaction.user_id == current_user:
                transactions_db.pop(i)
                return jsonify({'message': 'Transaction deleted successfully'}), 200
        
        return jsonify({'error': 'Transaction not found'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary', methods=['GET'])
@jwt_required()
def get_summary():
    try:
        current_user = get_jwt_identity()
        user_transactions = [t for t in transactions_db if t.user_id == current_user]
        
        cash_in = sum(t.amount for t in user_transactions if t.type == 'IN')
        cash_out = sum(t.amount for t in user_transactions if t.type == 'OUT')
        balance = cash_in - cash_out
        
        categories = {}
        for t in user_transactions:
            if t.category not in categories:
                categories[t.category] = {'in': 0, 'out': 0}
            if t.type == 'IN':
                categories[t.category]['in'] += t.amount
            else:
                categories[t.category]['out'] += t.amount
        
        return jsonify({
            'cash_in': cash_in,
            'cash_out': cash_out,
            'balance': balance,
            'categories': categories
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Dashboard analytics routes
@app.route('/api/dashboard')
@jwt_required()
def get_dashboard():
    try:
        current_user = get_jwt_identity()
        user_transactions = [t for t in transactions_db if t.user_id == current_user]
        
        # Get filters from query parameters
        type_filter = request.args.get('type', 'ALL')
        bank_filter = request.args.get('bank', 'ALL')
        
        # Apply filters
        filtered_transactions = user_transactions
        if type_filter != 'ALL':
            filtered_transactions = [t for t in filtered_transactions if t.type == type_filter]
        if bank_filter != 'ALL':
            filtered_transactions = [t for t in filtered_transactions if t.bank_cash == bank_filter]
        
        # Calculate summary
        cash_in = sum(t.amount for t in filtered_transactions if t.type == 'IN')
        cash_out = sum(t.amount for t in filtered_transactions if t.type == 'OUT')
        balance = cash_in - cash_out
        
        # Category breakdown
        category_breakdown = {}
        for t in filtered_transactions:
            key = f"{t.category}|{t.type}|{t.bank_cash}"
            if key not in category_breakdown:
                category_breakdown[key] = {
                    'category': t.category,
                    'type': t.type,
                    'bank_cash': t.bank_cash,
                    'amount': 0
                }
            category_breakdown[key]['amount'] += t.amount
        
        # Bank breakdown
        bank_breakdown = {}
        for t in filtered_transactions:
            if t.bank_cash not in bank_breakdown:
                bank_breakdown[t.bank_cash] = 0
            bank_breakdown[t.bank_cash] += t.amount
        
        return jsonify({
            'summary': {
                'cash_in': cash_in,
                'cash_out': cash_out,
                'balance': balance
            },
            'category_breakdown': list(category_breakdown.values()),
            'bank_breakdown': [{'bank_cash': k, 'amount': v} for k, v in bank_breakdown.items()]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/banks')
@jwt_required()
def get_banks():
    try:
        current_user = get_jwt_identity()
        user_transactions = [t for t in transactions_db if t.user_id == current_user]
        
        # Get unique banks/cash methods
        banks = list(set(t.bank_cash for t in user_transactions))
        return jsonify(banks), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
@jwt_required()
def get_categories():
    try:
        current_user = get_jwt_identity()
        user_transactions = [t for t in transactions_db if t.user_id == current_user]
        
        # Get unique categories
        categories = list(set(t.category for t in user_transactions))
        return jsonify(categories), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === Serve Frontend (Corrected Paths) ===

@app.route('/')
def serve_index():
    # Go UP one directory (../) and into 'frontend'
    return send_from_directory('../frontend', 'index.html')

@app.route('/login')
def serve_login():
    return send_from_directory('../frontend', 'login.html')

@app.route('/dashboard')
def serve_dashboard():
    return send_from_directory('../frontend', 'dashboard.html')

# This single route handles ALL other files (CSS, JS, images)
# You can delete your separate /styles.css, /script.js routes
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


