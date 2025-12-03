from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity
from datetime import datetime
import os
from sqlalchemy import func, distinct, extract
import csv
import io
import openpyxl

from config import Config
from models import db, User, Transaction
from extensions import db, bcrypt
from auth import authenticate_user

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
            if not User.query.filter_by(username="ZIYAD").first():
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
        token = authenticate_user(data.get('username'), data.get('password'))
        if token: return jsonify({'message': 'Success', 'access_token': token, 'username': data.get('username')}), 200
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/transactions', methods=['GET', 'POST'])
@app.route('/api/transactions/<int:transaction_id>', methods=['PUT', 'DELETE'])
@jwt_required()
def handle_transactions(transaction_id=None):
    try:
        current_user = get_current_user_obj()
        
        if request.method == 'GET':
            query = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc())
            
            # Filters
            if request.args.get('type') and request.args.get('type') != 'ALL':
                query = query.filter_by(type=request.args.get('type'))
            if request.args.get('bank') and request.args.get('bank') != 'ALL':
                query = query.filter_by(bank_cash=request.args.get('bank'))
            if request.args.get('category') and request.args.get('category') != 'ALL':
                query = query.filter_by(category=request.args.get('category'))
            if request.args.get('startDate'):
                query = query.filter(Transaction.date >= datetime.fromisoformat(request.args.get('startDate')))
            if request.args.get('endDate'):
                e_date = datetime.fromisoformat(request.args.get('endDate')).replace(hour=23, minute=59)
                query = query.filter(Transaction.date <= e_date)

            txns = query.all()
            return jsonify({'transactions': [t.to_dict() for t in txns]}), 200

        if request.method == 'POST':
            data = request.get_json()
            d = datetime.fromisoformat(data['date']) if data.get('date') else datetime.utcnow()
            new_t = Transaction(user_id=current_user.id, type=data['type'], amount=float(data['amount']), category=data['category'], remark=data.get('remark',''), bank_cash=data['bank_cash'], date=d)
            db.session.add(new_t)
            db.session.commit()
            return jsonify({'message': 'Added', 'transaction': new_t.to_dict()}), 201

        t = Transaction.query.get(transaction_id)
        if not t or t.user_id != current_user.id: return jsonify({'error': 'Not found'}), 404

        if request.method == 'DELETE':
            db.session.delete(t)
            db.session.commit()
            return jsonify({'message': 'Deleted'}), 200

        if request.method == 'PUT':
            data = request.get_json()
            if data.get('date'): 
                try: t.date = datetime.fromisoformat(data['date'])
                except: pass
            t.type = data['type']; t.amount = float(data['amount']); t.category = data['category']
            t.remark = data.get('remark', ''); t.bank_cash = data['bank_cash']
            db.session.commit()
            return jsonify({'message': 'Updated', 'transaction': t.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- HOME PAGE SUMMARY (Current Month Only) ---
@app.route('/api/summary', methods=['GET'])
@jwt_required()
def get_summary():
    try:
        current_user = get_current_user_obj()
        now = datetime.now()
        
        # Simple Cash Flow for Home Page (IN vs OUT) for CURRENT MONTH
        cash_in = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='IN')\
            .filter(extract('month', Transaction.date) == now.month)\
            .filter(extract('year', Transaction.date) == now.year).scalar() or 0
            
        cash_out = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=current_user.id, type='OUT')\
            .filter(extract('month', Transaction.date) == now.month)\
            .filter(extract('year', Transaction.date) == now.year).scalar() or 0
            
        return jsonify({
            'cash_in': cash_in,
            'cash_out': cash_out,
            'balance': cash_in - cash_out,
            'month_name': now.strftime("%B")
        }), 200
    except Exception as e: return jsonify({'error': str(e)}), 500

# --- Analytics Routes ---
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
        
        # Note: We usually need ALL types to calculate Net properly, 
        # so we apply type_filter at the end or for specific lists, 
        # but for the main calculation loop, we iterate all to find pairs.
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
        
        # 3. NET LOGIC CALCULATION
        
        lending_tracker = {} # Person -> Net Amount
        expense_tracker = {} # Category -> Net Amount
        asset_tracker = {}   # Category -> Net Amount
        
        total_income_cashflow = 0
        total_out_cashflow = 0
        
        for t in all_transactions:
            cat_lower = t.category.lower()
            
            # Global Cash Flow (Absolute values for Wallet Balance)
            if t.type == 'IN': total_income_cashflow += t.amount
            else: total_out_cashflow += t.amount
            
            # --- CATEGORY ROUTING ---
            
            # A. Lending (Net Calculation)
            if cat_lower in lending_keywords:
                person = t.remark.strip() if t.remark else "Unknown"
                if person not in lending_tracker: lending_tracker[person] = 0
                
                # OUT = Money given (+ Debt), IN = Money returned (- Debt)
                if t.type == 'OUT': lending_tracker[person] += t.amount
                else: lending_tracker[person] -= t.amount

            # B. Assets (Net Calculation)
            elif cat_lower in asset_keywords:
                if t.category not in asset_tracker: asset_tracker[t.category] = 0
                
                # OUT = Buy Asset (+ Asset), IN = Sell/Withdraw (- Asset)
                if t.type == 'OUT': asset_tracker[t.category] += t.amount
                else: asset_tracker[t.category] -= t.amount

            # C. Expenses (Net Calculation)
            else:
                # This handles the "Friends" logic:
                # OUT 500, IN 250 = Net Expense 250.
                if t.category not in expense_tracker: expense_tracker[t.category] = 0
                
                if t.type == 'OUT': 
                    expense_tracker[t.category] += t.amount
                else: 
                    # Type IN: Treat as refund/reduction of expense
                    expense_tracker[t.category] -= t.amount

        # 4. AGGREGATION FOR DISPLAY
        
        # Sum up Net Lending (Only positive = people owe you)
        net_lent = sum(v for v in lending_tracker.values())
        
        # Sum up Net Assets
        net_assets = sum(v for v in asset_tracker.values())
        
        # Sum up Net Expenses 
        # Only count positive values. If a category is negative (e.g. Salary), ignore it for "Expense" total.
        net_expenses = sum(v for v in expense_tracker.values() if v > 0)
        
        # Total Money Out (Net Expenses + Net Assets + Net Lent)
        total_money_out = net_expenses + net_assets + (net_lent if net_lent > 0 else 0)
        
        # Balance = Actual Cash In - Actual Cash Out (Wallet Reality)
        balance = total_income_cashflow - total_out_cashflow

        # 5. PREPARE CHART DATA
        
        # Expense Chart: Only show categories where Net Spend > 0
        expense_list = [{'category': k, 'amount': v} for k, v in expense_tracker.items() if v > 0]
        
        # Lending Chart: Show net balance per person
        lending_list = [{'person': k, 'amount': v} for k, v in lending_tracker.items() if v != 0]
        
        # Asset Chart
        asset_list = []
        for k, v in asset_tracker.items():
            # Use Category as the label for colors, but Remark is not strictly needed for grouping here 
            # unless you want to see specific investments. Let's keep it simple: Category.
            asset_list.append({'category': k, 'amount': v, 'remark': k})
            
        # Money Out Chart (Expenses + Assets)
        money_out_list = expense_list + [{'category': k, 'amount': v} for k, v in asset_tracker.items() if v > 0]

        return jsonify({
            'summary': {
                'income': total_income_cashflow,
                'expenses': net_expenses,
                'assets': net_assets,
                'lent': net_lent,
                'balance': balance,
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

# --- Helpers ---
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
        
        if file.filename.endswith('.csv'):
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            for row in csv_reader:
                if row.get('Date') and row.get('Amount'):
                    try:
                        t_date = datetime.utcnow()
                        try: t_date = datetime.fromisoformat(row['Date'])
                        except: pass
                        t = Transaction(user_id=current_user.id, type=row.get('Type','OUT'), amount=float(row.get('Amount',0)), category=row.get('Category','Uncategorized'), remark=row.get('Remark',''), bank_cash=row.get('Bank/Cash','Cash'), date=t_date)
                        transactions_to_add.append(t)
                    except: continue
        elif file.filename.endswith(('.xls', '.xlsx')):
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            headers = [cell.value for cell in sheet[1]]
            for row in sheet.iter_rows(min_row=2, values_only=True):
                data = dict(zip(headers, row))
                if data.get('Date') and data.get('Amount'):
                    t_date = data['Date'] if isinstance(data['Date'], datetime) else datetime.utcnow()
                    t = Transaction(user_id=current_user.id, type=data.get('Type','OUT'), amount=float(data.get('Amount',0)), category=data.get('Category','Uncategorized'), remark=data.get('Remark','') or '', bank_cash=data.get('Bank/Cash','Cash'), date=t_date)
                    transactions_to_add.append(t)

        if transactions_to_add:
            db.session.add_all(transactions_to_add); db.session.commit()
            return jsonify({'message': f'{len(transactions_to_add)} imported'}), 200
        return jsonify({'message': 'No data'}), 400
    except Exception as e: return jsonify({'error': str(e)}), 500

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
