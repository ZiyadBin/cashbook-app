// For development - will update to your Heroku URL after deployment
const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000/api' 
    : 'https://your-cashbook-backend.herokuapp.com/api';

let token = localStorage.getItem('token');
let currentUser = localStorage.getItem('username');

// Check authentication on page load
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.endsWith('login.html') || window.location.pathname === '/') {
        if (token && currentUser) {
            window.location.href = 'index.html';
        }
    } else {
        if (!token || !currentUser) {
            window.location.href = 'login.html';
        } else {
            document.getElementById('usernameDisplay').textContent = `Welcome, ${currentUser}`;
            loadTransactions();
            loadSummary();
        }
    }
});

// Login functionality
if (document.getElementById('loginForm')) {
    document.getElementById('loginForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('username', data.username);
                window.location.href = 'index.html';
            } else {
                showMessage(data.error, 'error');
            }
        } catch (error) {
            showMessage('Login failed: ' + error.message, 'error');
        }
    });
}

// Transaction functionality
if (document.getElementById('transactionForm')) {
    document.getElementById('transactionForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const transaction = {
            type: document.getElementById('type').value,
            amount: parseFloat(document.getElementById('amount').value),
            category: document.getElementById('category').value,
            remark: document.getElementById('remark').value,
            bank_cash: document.getElementById('bankCash').value
        };
        
        try {
            const response = await fetch(`${API_BASE}/transactions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(transaction)
            });
            
            if (response.ok) {
                document.getElementById('transactionForm').reset();
                loadTransactions();
                loadSummary();
                showMessage('Transaction added successfully!', 'success');
            } else {
                const data = await response.json();
                showMessage(data.error, 'error');
            }
        } catch (error) {
            showMessage('Failed to add transaction: ' + error.message, 'error');
        }
    });
}

// Load transactions
async function loadTransactions() {
    try {
        const response = await fetch(`${API_BASE}/transactions`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            displayTransactions(data.transactions);
        }
    } catch (error) {
        console.error('Failed to load transactions:', error);
    }
}

// Display transactions in table
function displayTransactions(transactions) {
    const tbody = document.getElementById('transactionsBody');
    tbody.innerHTML = '';
    
    transactions.forEach(transaction => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${new Date(transaction.date).toLocaleDateString()}</td>
            <td><span class="type-${transaction.type.toLowerCase()}">${transaction.type}</span></td>
            <td>$${parseFloat(transaction.amount).toFixed(2)}</td>
            <td>${transaction.category}</td>
            <td>${transaction.remark}</td>
            <td>${transaction.bank_cash}</td>
            <td><button onclick="deleteTransaction('${transaction.transaction_id}')" class="btn-danger">Delete</button></td>
        `;
        tbody.appendChild(row);
    });
}

// Load summary
async function loadSummary() {
    try {
        const response = await fetch(`${API_BASE}/summary`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            document.getElementById('cashIn').textContent = `$${data.cash_in.toFixed(2)}`;
            document.getElementById('cashOut').textContent = `$${data.cash_out.toFixed(2)}`;
            document.getElementById('balance').textContent = `$${data.balance.toFixed(2)}`;
        }
    } catch (error) {
        console.error('Failed to load summary:', error);
    }
}

// Delete transaction
async function deleteTransaction(transactionId) {
    if (!confirm('Are you sure you want to delete this transaction?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/transactions/${transactionId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            loadTransactions();
            loadSummary();
            showMessage('Transaction deleted successfully!', 'success');
        } else {
            const data = await response.json();
            showMessage(data.error, 'error');
        }
    } catch (error) {
        showMessage('Failed to delete transaction: ' + error.message, 'error');
    }
}

// Logout
function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    window.location.href = 'login.html';
}

// Utility functions
function showMessage(message, type) {
    const messageDiv = document.getElementById('message');
    if (messageDiv) {
        messageDiv.textContent = message;
        messageDiv.className = `message ${type}`;
        setTimeout(() => {
            messageDiv.textContent = '';
            messageDiv.className = 'message';
        }, 5000);
    } else {
        alert(message);
    }
}
