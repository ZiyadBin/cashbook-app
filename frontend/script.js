const API_BASE = '/api';

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
            
            // Set default date to current India time
            const now = new Date();
            const timezoneOffset = 5.5 * 60 * 60 * 1000; // IST offset in milliseconds
            const indiaTime = new Date(now.getTime() + timezoneOffset);
            const localDateTime = indiaTime.toISOString().slice(0, 16);
            
            if (document.getElementById('date')) {
                document.getElementById('date').value = localDateTime;
            }
            
            loadTransactions();
            loadSummary();
            if (document.getElementById('categoryList')) {
                loadDropdowns();
            }
            setupModal();
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

// Navigation to dashboard
function goToDashboard() {
    window.location.href = 'dashboard.html';
}

// Load categories and banks for dropdowns
async function loadDropdowns() {
    try {
        // Load categories
        const catResponse = await fetch(`${API_BASE}/categories`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (catResponse.ok) {
            const categories = await catResponse.json();
            const categoryList = document.getElementById('categoryList');
            if (categoryList) {
                categoryList.innerHTML = '';
                categories.forEach(cat => {
                    const option = document.createElement('option');
                    option.value = cat;
                    categoryList.appendChild(option);
                });
            }
        }
        
        // Load banks
        const bankResponse = await fetch(`${API_BASE}/banks`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (bankResponse.ok) {
            const banks = await bankResponse.json();
            const bankList = document.getElementById('bankList');
            if (bankList) {
                bankList.innerHTML = '';
                banks.forEach(bank => {
                    const option = document.createElement('option');
                    option.value = bank;
                    bankList.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error('Failed to load dropdowns:', error);
    }
}

// Transaction functionality
if (document.getElementById('transactionForm')) {
    document.getElementById('transactionForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const transaction = {
            date: document.getElementById('date').value,
            type: document.getElementById('type').value,
            amount: parseFloat(document.getElementById('amount').value),
            category: document.getElementById('category').value,
            remark: document.getElementById('remark').value || '',
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
                
                // Reset date to current India time
                const now = new Date();
                const timezoneOffset = 5.5 * 60 * 60 * 1000;
                const indiaTime = new Date(now.getTime() + timezoneOffset);
                const localDateTime = indiaTime.toISOString().slice(0, 16);
                document.getElementById('date').value = localDateTime;
                
                loadTransactions();
                loadSummary();
                loadDropdowns();
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
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    transactions.forEach(transaction => {
        const row = document.createElement('tr');
        const transactionDate = new Date(transaction.date);
        const formattedDate = transactionDate.toLocaleString('en-IN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        row.innerHTML = `
            <td>${formattedDate}</td>
            <td><span class="type-${transaction.type.toLowerCase()}">${transaction.type}</span></td>
            <td>₹${parseFloat(transaction.amount).toFixed(2)}</td>
            <td>${transaction.category}</td>
            <td>${transaction.remark}</td>
            <td>${transaction.bank_cash}</td>
            <td>
                <button onclick="editTransaction('${transaction.transaction_id}')" class="btn-secondary" style="margin-right: 5px;">Edit</button>
                <button onclick="deleteTransaction('${transaction.transaction_id}')" class="btn-danger">Delete</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Edit transaction
async function editTransaction(transactionId) {
    try {
        const response = await fetch(`${API_BASE}/transactions`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            const transaction = data.transactions.find(t => t.transaction_id === transactionId);
            
            if (transaction) {
                // Convert date to local datetime format
                const transactionDate = new Date(transaction.date);
                const localDateTime = transactionDate.toISOString().slice(0, 16);
                
                document.getElementById('editTransactionId').value = transaction.transaction_id;
                document.getElementById('editDate').value = localDateTime;
                document.getElementById('editType').value = transaction.type;
                document.getElementById('editAmount').value = transaction.amount;
                document.getElementById('editCategory').value = transaction.category;
                document.getElementById('editBankCash').value = transaction.bank_cash;
                document.getElementById('editRemark').value = transaction.remark;
                
                openModal();
            }
        }
    } catch (error) {
        console.error('Failed to load transaction for editing:', error);
    }
}

// Update transaction
if (document.getElementById('editTransactionForm')) {
    document.getElementById('editTransactionForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const transactionId = document.getElementById('editTransactionId').value;
        const transaction = {
            date: document.getElementById('editDate').value,
            type: document.getElementById('editType').value,
            amount: parseFloat(document.getElementById('editAmount').value),
            category: document.getElementById('editCategory').value,
            remark: document.getElementById('editRemark').value || '',
            bank_cash: document.getElementById('editBankCash').value
        };
        
        try {
            const response = await fetch(`${API_BASE}/transactions/${transactionId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(transaction)
            });
            
            if (response.ok) {
                closeModal();
                loadTransactions();
                loadSummary();
                loadDropdowns();
                showMessage('Transaction updated successfully!', 'success');
            } else {
                const data = await response.json();
                showMessage(data.error, 'error');
            }
        } catch (error) {
            showMessage('Failed to update transaction: ' + error.message, 'error');
        }
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
            if (document.getElementById('cashIn')) {
                document.getElementById('cashIn').textContent = `₹${data.cash_in.toFixed(2)}`;
            }
            if (document.getElementById('cashOut')) {
                document.getElementById('cashOut').textContent = `₹${data.cash_out.toFixed(2)}`;
            }
            if (document.getElementById('balance')) {
                document.getElementById('balance').textContent = `₹${data.balance.toFixed(2)}`;
            }
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
            loadDropdowns();
            showMessage('Transaction deleted successfully!', 'success');
        } else {
            const data = await response.json();
            showMessage(data.error, 'error');
        }
    } catch (error) {
        showMessage('Failed to delete transaction: ' + error.message, 'error');
    }
}

// Modal functions
function setupModal() {
    const modal = document.getElementById('editModal');
    const span = document.getElementsByClassName('close')[0];
    
    if (span) {
        span.onclick = function() {
            closeModal();
        }
    }
    
    if (modal) {
        window.onclick = function(event) {
            if (event.target == modal) {
                closeModal();
            }
        }
    }
}

function openModal() {
    const modal = document.getElementById('editModal');
    if (modal) {
        modal.style.display = 'block';
    }
}

function closeModal() {
    const modal = document.getElementById('editModal');
    if (modal) {
        modal.style.display = 'none';
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
