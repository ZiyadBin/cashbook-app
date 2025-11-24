from flask import Flask, request, jsonify, send_from_directory, make_response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import datetime, date
import os
from sqlalchemy import func, distinct, extract
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

@app.before_request
def setup_database():
    if not hasattr(app, 'database_initialized'):
        with app.app_context():
            db.create_all()
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

# --- Routes ---

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

@app.route('/api/transactions', methods=['GET'])
@jwt_required()
def get_transactions():
    try:
        current_user = get_current_user_obj()
        # Return ALL transactions (frontend will handle showing only 5)
        user_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc()).all()
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
        
        new_transaction = Transaction(
            user_id=current_user.id,
            type=data['type'],
            amount=float(data['amount']),
            category=data['category'],
            remark=data.get('remark', ''),
            bank_cash=data['bank_cash'],
            date=transaction_date
        )
        db.session.add(new_transaction)
        db.session.commit()
        return jsonify({'message': 'Transaction added successfully', 'transaction': new_transaction.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
@jwt_required()
def update_transaction(transaction_id):
    try:
        current_user = get_current_user_obj()
        data = request.get_json()
        transaction = Transaction.query.get(transaction_id)
        
        if not transaction or transaction.user_id != current_user.id:
            return jsonify({'error': 'Transaction not found'}), 404
        
        if data.get('date'):
            try:
                transaction.date = datetime.fromisoformat(data['date'])
            except ValueError:
                pass
        
        transaction.type = data['type']
        transaction.amount = float(data['amount'])
        transaction.category = data['category']
        transaction.remark = data.get('remark', '')
        transaction.bank_cash = data['bank_cash']
        db.session.commit()
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
        db.session.delete(transaction)
        db.session.commit()
        return jsonify({'message': 'Transaction deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary', methods=['GET'])
@jwt_required()
def get_summary():
    try:
        current_user = get_current_user_obj()
        
        # Get current month and year
        now = datetime.now()
        current_month = now.month
        current_year = now.year

        # Filter by User AND Current Month AND Current Year
        cash_in = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='IN')\
            .filter(extract('month', Transaction.date) == current_month)\
            .filter(extract('year', Transaction.date) == current_year).scalar() or 0
            
        cash_out = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='OUT')\
            .filter(extract('month', Transaction.date) == current_month)\
            .filter(extract('year', Transaction.date) == current_year).scalar() or 0
            
        balance = cash_in - cash_out
        
        return jsonify({
            'cash_in': cash_in,
            'cash_out': cash_out,
            'balance': balance,
            'month_name': now.strftime("%B") # Return month name to display
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Analytics Routes ---
@app.route('/api/dashboard')
@jwt_required()
def get_dashboard():
    try:
        current_user = get_current_user_obj()
        
        # --- 1. FILTERING ---
        query = Transaction.query.filter_by(user_id=current_user.id)
        
        type_filter = request.args.get('type', 'ALL')
        bank_filter = request.args.get('bank', 'ALL')
        cat_filter = request.args.get('category', 'ALL')
        start_date = request.args.get('startDate', '')
        end_date = request.args.get('endDate', '')
        
        if type_filter != 'ALL': query = query.filter_by(type=type_filter)
        if bank_filter != 'ALL': query = query.filter_by(bank_cash=bank_filter)
        if cat_filter != 'ALL': query = query.filter_by(category=cat_filter)
        
        # Date Range Filter
        if start_date:
            query = query.filter(Transaction.date >= datetime.fromisoformat(start_date))
        if end_date:
            # Add 23:59:59 to include the full end day
            e_date = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
            query = query.filter(Transaction.date <= e_date)
        
        all_transactions = query.all()
        
        # --- 2. DEFINITIONS ---
        asset_keywords = ['savings', 'saving', 'investment', 'investments', 'asset', 'assets', 'sip', 'stocks', 'mutual fund', 'gold', 'pf', 'ppf']
        lending_keywords = ['lent', 'loan', 'given', 'borrowed']
        
        # --- 3. NET CALCULATION LOGIC ---
        
        # A. Lending (Tracked by Person/Remark)
        lending_tracker = {} 
        
        # B. Real Expenses (Tracked by Category, Net)
        expense_tracker = {}
        
        # C. Assets (Tracked by Category, Net)
        asset_tracker = {}
        
        # D. Income (Pure Income categories only)
        total_income = 0
        
        for t in all_transactions:
            cat_lower = t.category.lower()
            
            # --- LOGIC 1: LENDING ---
            if cat_lower in lending_keywords:
                person = t.remark.strip() if t.remark else "Unknown"
                if person not in lending_tracker: lending_tracker[person] = 0
                
                # If OUT, they owe us (+). If IN, they paid back (-).
                if t.type == 'OUT': lending_tracker[person] += t.amount
                else: lending_tracker[person] -= t.amount

            # --- LOGIC 2: ASSETS ---
            elif cat_lower in asset_keywords:
                if t.category not in asset_tracker: asset_tracker[t.category] = 0
                
                # If OUT, we bought asset (+). If IN, we sold/withdrew (-).
                if t.type == 'OUT': asset_tracker[t.category] += t.amount
                else: asset_tracker[t.category] -= t.amount

            # --- LOGIC 3: EXPENSES vs INCOME ---
            else:
                if t.type == 'IN':
                    # Check if this is a refund for an existing expense category or pure income
                    # Simplified: We count IN as Income, UNLESS we calculate Net Expense later.
                    # For this logic: Pure Income is money coming in that isn't a refund.
                    # But user wants "Credit Card IN" to reduce "Credit Card OUT".
                    
                    # We will treat this as a "Negative Expense" for calculation
                    if t.category not in expense_tracker: expense_tracker[t.category] = 0
                    expense_tracker[t.category] -= t.amount
                    
                    # Also track as Total Gross Income for the top card
                    total_income += t.amount
                else:
                    # Type OUT
                    if t.category not in expense_tracker: expense_tracker[t.category] = 0
                    expense_tracker[t.category] += t.amount

        # --- 4. FINAL AGGREGATION ---
        
        # Calculate Total Net Lending (Money currently outside)
        net_lent_total = sum(amount for amount in lending_tracker.values() if amount > 0)
        
        # Calculate Total Net Assets (Total saved)
        net_assets_total = sum(asset_tracker.values())
        
        # Calculate Total Net Expenses (Only positive values, effectively Expense - Refunds)
        # If a category is negative (e.g. got more refunds than spent), it's technically income, 
        # but for dashboard we usually just show 0 or negative.
        net_expense_total = sum(amount for amount in expense_tracker.values())
        
        # Total Money Out (The "Big Bar") = Expenses + Assets + Pending Lending
        total_money_out = net_expense_total + net_assets_total + net_lent_total
        
        # Current Balance (from filtered set)
        # Note: calculating balance from a filtered date range is tricky (it shows "Cash Flow" for that period)
        # To show actual wallet balance, we usually need ALL time. 
        # But for this view, let's show Cash Flow Balance (Net Change)
        net_balance = total_income - (sum(t.amount for t in all_transactions if t.type == 'OUT'))

        # Format Lists for Frontend
        # 1. Lending: Only show people who owe money (> 0)
        lending_list = [{'person': k, 'amount': v} for k, v in lending_tracker.items() if v != 0]
        
        # 2. Assets: All assets
        asset_list = [{'category': k, 'amount': v} for k, v in asset_tracker.items()]
        
        # 3. Expenses: Only categories with Net Spend > 0
        expense_list = [{'category': k, 'amount': v} for k, v in expense_tracker.items() if v > 0]

        return jsonify({
            'summary': {
                'income': total_income,
                'expenses': net_expense_total,
                'assets': net_assets_total,
                'lent': net_lent_total,
                'balance': net_balance,
                'total_money_out': total_money_out
            },
            'expense_chart': expense_list,
            'lending_chart': lending_list,
            'asset_chart': asset_list
        }), 200
        
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

@app.route('/api/banks')
@jwt_required()
def get_banks():
    try:
        current_user = get_current_user_obj()
        banks = db.session.query(distinct(Transaction.bank_cash)).filter_by(user_id=current_user.id).all()
        return jsonify([b[0] for b in banks]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories')
@jwt_required()
def get_categories():
    try:
        current_user = get_current_user_obj()
        categories = db.session.query(distinct(Transaction.category)).filter_by(user_id=current_user.id).all()
        return jsonify([c[0] for c in categories]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Import Route ---
@app.route('/api/import', methods=['POST'])
@jwt_required()
def import_transactions():
    try:
        current_user = get_current_user_obj()
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        transactions_to_add = []
        
        # Handle CSV
        if file.filename.endswith('.csv'):
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            for row in csv_reader:
                # Basic validation logic
                if row.get('Date') and row.get('Amount'):
                    try:
                         # Try parsing date, fallback to now
                        t_date = datetime.utcnow()
                        if row.get('Date'):
                             try: t_date = datetime.strptime(row['Date'], '%d/%m/%Y, %I:%M %p') # Try Excel format
                             except: 
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
                    except Exception as e:
                        continue # Skip bad rows

        # Handle Excel
        elif file.filename.endswith(('.xls', '.xlsx')):
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            headers = [cell.value for cell in sheet[1]]
            for row in sheet.iter_rows(min_row=2, values_only=True):
                data = dict(zip(headers, row))
                if data.get('Date') and data.get('Amount'):
                    # Excel usually handles dates as objects, so simpler
                    t_date = data['Date'] if isinstance(data['Date'], datetime) else datetime.utcnow()
                    t = Transaction(
                        user_id=current_user.id,
                        type=data.get('Type', 'OUT'),
                        amount=float(data.get('Amount', 0)),
                        category=data.get('Category', 'Uncategorized'),
                        remark=data.get('Remark', '') if data.get('Remark') else '',
                        bank_cash=data.get('Bank/Cash', 'Cash'),
                        date=t_date
                    )
                    transactions_to_add.append(t)

        if transactions_to_add:
            db.session.add_all(transactions_to_add)
            db.session.commit()
            return jsonify({'message': f'{len(transactions_to_add)} transactions imported successfully'}), 200
        else:
            return jsonify({'message': 'No valid transactions found in file'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Frontend ---
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
