from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import datetime
import os
from sqlalchemy import func, distinct
import csv
import io
import openpyxl

from config import Config
from models import db, User, Transaction
from extensions import db, bcrypt
from auth import authenticate_user

# --- App Initialization ---

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)
CORS(app)

# --- Database Setup ---
@app.before_request
def setup_database():
    if not hasattr(app, 'database_initialized'):
        with app.app_context():
            db.create_all()
            # Create default user if not exists
            user = User.query.filter_by(username="ZIYAD").first()
            if not user:
                default_user = User(username="ZIYAD")
                default_user.set_password("Admin123")
                db.session.add(default_user)
                db.session.commit()
        app.database_initialized = True

def get_current_user_obj():
    username = get_jwt_identity()
    return User.query.filter_by(username=username).first()

# --- Authentication ---

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
            return jsonify({'message': 'Login successful', 'access_token': token, 'username': username}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Transactions (CRUD + Filtered List) ---

@app.route('/api/transactions', methods=['GET', 'POST'])
@app.route('/api/transactions/<int:transaction_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def handle_transactions(transaction_id=None):
    try:
        current_user = get_current_user_obj()

        # 1. GET LIST (With Filters)
        if request.method == 'GET':
            query = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc())
            
            # Apply Filters (Matches Dashboard Logic)
            type_f = request.args.get('type', 'ALL')
            bank_f = request.args.get('bank', 'ALL')
            cat_f = request.args.get('category', 'ALL')
            start_d = request.args.get('startDate')
            end_d = request.args.get('endDate')

            if type_f != 'ALL': query = query.filter_by(type=type_f)
            if bank_f != 'ALL': query = query.filter_by(bank_cash=bank_f)
            if cat_f != 'ALL': query = query.filter_by(category=cat_f)
            
            if start_d:
                query = query.filter(Transaction.date >= datetime.fromisoformat(start_d))
            if end_d:
                e_date = datetime.fromisoformat(end_d).replace(hour=23, minute=59, second=59)
                query = query.filter(Transaction.date <= e_date)

            txns = query.all()
            return jsonify({'transactions': [t.to_dict() for t in txns]}), 200

        # 2. POST (Add New)
        if request.method == 'POST':
            data = request.get_json()
            # Handle Date
            if data.get('date'):
                try: d = datetime.fromisoformat(data['date'])
                except: d = datetime.utcnow()
            else: d = datetime.utcnow()

            new_t = Transaction(
                user_id=current_user.id,
                type=data['type'],
                amount=float(data['amount']),
                category=data['category'],
                remark=data.get('remark', ''),
                bank_cash=data['bank_cash'],
                date=d
            )
            db.session.add(new_t)
            db.session.commit()
            return jsonify({'message': 'Added', 'transaction': new_t.to_dict()}), 201

        # For PUT/DELETE, we need an ID
        t = Transaction.query.get(transaction_id)
        if not t or t.user_id != current_user.id:
            return jsonify({'error': 'Not found'}), 404

        # 3. DELETE
        if request.method == 'DELETE':
            db.session.delete(t)
            db.session.commit()
            return jsonify({'message': 'Deleted'}), 200

        # 4. PUT (Update)
        if request.method == 'PUT':
            data = request.get_json()
            if data.get('date'): 
                try: t.date = datetime.fromisoformat(data['date'])
                except: pass
            
            t.type = data['type']
            t.amount = float(data['amount'])
            t.category = data['category']
            t.remark = data.get('remark', '')
            t.bank_cash = data['bank_cash']
            
            db.session.commit()
            return jsonify({'message': 'Updated', 'transaction': t.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- Dashboard Analytics (The New Logic) ---

@app.route('/api/dashboard')
@jwt_required()
def get_dashboard():
    try:
        current_user = get_current_user_obj()
        
        # 1. Base Query with Filters
        query = Transaction.query.filter_by(user_id=current_user.id)
        
        type_filter = request.args.get('type', 'ALL')
        bank_filter = request.args.get('bank', 'ALL')
        cat_filter = request.args.get('category', 'ALL')
        start_date = request.args.get('startDate', '')
        end_date = request.args.get('endDate', '')
        
        if type_filter != 'ALL': query = query.filter_by(type=type_filter)
        if bank_filter != 'ALL': query = query.filter_by(bank_cash=bank_filter)
        if cat_filter != 'ALL': query = query.filter_by(category=cat_filter)
        
        if start_date:
            query = query.filter(Transaction.date >= datetime.fromisoformat(start_date))
        if end_date:
            e_date = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
            query = query.filter(Transaction.date <= e_date)
        
        all_transactions = query.all()
        
        # 2. Definitions
        asset_keywords = ['savings', 'saving', 'investment', 'investments', 'asset', 'assets', 'sip', 'stocks', 'mutual fund', 'gold', 'pf', 'ppf']
        lending_keywords = ['lent', 'loan', 'given', 'borrowed']
        
        # 3. NET Logic Implementation
        
        # Buckets to track Net Values
        lending_tracker = {} # Person -> Net Amount
        expense_tracker = {} # Category -> Net Amount
        asset_tracker = {}   # Category -> Net Amount
        
        # Cash Flow Totals
        total_in_cashflow = 0
        total_out_cashflow = 0
        
        for t in all_transactions:
            cat_lower = t.category.lower()
            
            # Track Cash Flow (Absolute In/Out)
            if t.type == 'IN': total_in_cashflow += t.amount
            else: total_out_cashflow += t.amount
            
            # --- Logic A: Lending ---
            if cat_lower in lending_keywords:
                person = t.remark.strip() if t.remark else "Unknown"
                if person not in lending_tracker: lending_tracker[person] = 0
                
                if t.type == 'OUT': lending_tracker[person] += t.amount # We gave money
                else: lending_tracker[person] -= t.amount # They paid back

            # --- Logic B: Assets ---
            elif cat_lower in asset_keywords:
                if t.category not in asset_tracker: asset_tracker[t.category] = 0
                
                if t.type == 'OUT': asset_tracker[t.category] += t.amount # Bought asset
                else: asset_tracker[t.category] -= t.amount # Sold asset

            # --- Logic C: Expenses ---
            else:
                if t.category not in expense_tracker: expense_tracker[t.category] = 0
                
                if t.type == 'OUT': expense_tracker[t.category] += t.amount # Spent
                else: expense_tracker[t.category] -= t.amount # Refund/Cashback

        # 4. Aggregation
        
        # Net calculations for display
        net_lent_total = sum(v for v in lending_tracker.values())
        net_assets_total = sum(v for v in asset_tracker.values())
        net_expense_total = sum(v for v in expense_tracker.values())
        
        # Balance is simple Cash Flow (Money I have right now)
        current_balance = total_in_cashflow - total_out_cashflow
        
        # Total "Money Out" visualization (Net Exp + Net Assets + Net Lent)
        total_money_out = net_expense_total + net_assets_total + net_lent_total

        # Chart Data Preparation
        # 1. Lending Chart (Person vs Amount)
        lending_list = [{'person': k, 'amount': v} for k, v in lending_tracker.items() if v != 0]
        
        # 2. Asset Chart (Category vs Amount)
        asset_list = []
        for k, v in asset_tracker.items():
            # Find a remark for this category to display if needed, or just use category
            asset_list.append({'category': k, 'amount': v, 'remark': k}) 
            
        # 3. Expense Chart (Category vs Amount) - Only show positive expenses
        expense_list = [{'category': k, 'amount': v} for k, v in expense_tracker.items() if v > 0]
        
        # 4. Money Out Chart (Expenses + Assets Categories)
        money_out_list = expense_list + asset_list

        return jsonify({
            'summary': {
                'income': total_in_cashflow, # Gross Income
                'expenses': net_expense_total,
                'assets': net_assets_total,
                'lent': net_lent_total,
                'balance': current_balance,
                'total_money_out': total_money_out
            },
            'expense_chart': expense_list,
            'lending_chart': lending_list,
            'asset_chart': asset_list,
            'money_out_chart': money_out_list
        }), 200
        
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

# --- Helpers & Import ---

@app.route('/api/banks', methods=['GET'])
@jwt_required()
def get_banks():
    try:
        banks = db.session.query(distinct(Transaction.bank_cash)).filter_by(user_id=get_current_user_obj().id).all()
        return jsonify([b[0] for b in banks]), 200
    except: return jsonify([]), 200

@app.route('/api/categories', methods=['GET'])
@jwt_required()
def get_categories():
    try:
        cats = db.session.query(distinct(Transaction.category)).filter_by(user_id=get_current_user_obj().id).all()
        return jsonify([c[0] for c in cats]), 200
    except: return jsonify([]), 200

@app.route('/api/import', methods=['POST'])
@jwt_required()
def import_transactions():
    try:
        current_user = get_current_user_obj()
        if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
        file = request.files['file']
        
        transactions_to_add = []
        
        # CSV Import
        if file.filename.endswith('.csv'):
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            for row in csv_reader:
                if row.get('Date') and row.get('Amount'):
                    try:
                        t_date = datetime.utcnow()
                        try: t_date = datetime.fromisoformat(row['Date'])
                        except: pass
                        
                        t = Transaction(
                            user_id=current_user.id,
                            type=row.get('Type', 'OUT'),
                            amount=float(row.get('Amount', 0)),
                            category=row.get('Category', 'Uncategorized'),
                            remark=row.get('Remark', ''),
                            bank_cash=row.get('Bank/Cash', 'Cash'),
                            date=t_date
                        )
                        transactions_to_add.append(t)
                    except: continue

        # Excel Import
        elif file.filename.endswith(('.xls', '.xlsx')):
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            headers = [cell.value for cell in sheet[1]]
            for row in sheet.iter_rows(min_row=2, values_only=True):
                data = dict(zip(headers, row))
                if data.get('Date') and data.get('Amount'):
                    t_date = data['Date'] if isinstance(data['Date'], datetime) else datetime.utcnow()
                    t = Transaction(
                        user_id=current_user.id,
                        type=data.get('Type', 'OUT'),
                        amount=float(data.get('Amount', 0)),
                        category=data.get('Category', 'Uncategorized'),
                        remark=data.get('Remark', '') or '',
                        bank_cash=data.get('Bank/Cash', 'Cash'),
                        date=t_date
                    )
                    transactions_to_add.append(t)

        if transactions_to_add:
            db.session.add_all(transactions_to_add)
            db.session.commit()
            return jsonify({'message': f'{len(transactions_to_add)} imported'}), 200
        return jsonify({'message': 'No data found'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Frontend Serving ---
@app.route('/')
def serve_index(): return send_from_directory('../frontend/pages', 'index.html')
@app.route('/login')
def serve_login(): return send_from_directory('../frontend/pages', 'login.html')
@app.route('/dashboard')
def serve_dashboard(): return send_from_directory('../frontend/pages', 'dashboard.html')
@app.route('/<path:path>')
def serve_static(path): return send_from_directory('../frontend', path)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
