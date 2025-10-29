#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from flask import Flask, request, jsonify
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
        
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            user_id=current_user,
            type=data['type'],
            amount=float(data['amount']),
            category=data['category'],
            remark=data['remark'],
            bank_cash=data['bank_cash']
        )
        
        transactions_db.append(transaction)
        return jsonify({'message': 'Transaction added successfully', 'transaction': transaction.to_dict()}), 201
        
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
        
        # Category breakdown
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

@app.route('/')
def home():
    return jsonify({"message": "Cash Book API is running!", "status": "OK"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

