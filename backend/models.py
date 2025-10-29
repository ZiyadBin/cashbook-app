#!/usr/bin/env python
# coding: utf-8

# In[ ]:


from datetime import datetime

# In-memory database (we'll upgrade to real database later)
users_db = {
    "ZIYAD": {
        "password": "Admin123",
        "user_id": "ZIYAD"
    }
}

transactions_db = []

class Transaction:
    def __init__(self, transaction_id, user_id, type, amount, category, remark, bank_cash, date=None):
        self.transaction_id = transaction_id
        self.user_id = user_id
        self.type = type  # 'IN' or 'OUT'
        self.amount = amount
        self.category = category
        self.remark = remark
        self.bank_cash = bank_cash
        self.date = date or datetime.now()
    
    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'user_id': self.user_id,
            'type': self.type,
            'amount': self.amount,
            'category': self.category,
            'remark': self.remark,
            'bank_cash': self.bank_cash,
            'date': self.date.isoformat()
        }

