const API_BASE = '/api';
let token = localStorage.getItem('token');
let currentUser = localStorage.getItem('username');

// --- Auth Check on Page Load ---
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname === '/login') {
        // If on login page and already logged in, go to dashboard
        if (token && currentUser) { window.location.href = '/'; }
    } else {
        // If not on login page and NOT logged in, go to login
        if (!token || !currentUser) { window.location.href = '/login'; } 
        else { initializeApp(); }
    }
});

function initializeApp() {
    if(document.getElementById('usernameDisplay')) {
        document.getElementById('usernameDisplay').textContent = `Hi, ${currentUser}`;
    }
    
    // Set local date for input
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset()); 
    if (document.getElementById('date')) {
        document.getElementById('date').value = now.toISOString().slice(0, 16);
    }
    
    loadTransactions();
    loadSummary();
    loadDropdowns();
}

// ==========================================
//  MISSING LOGIN LOGIC (ADDED BACK)
// ==========================================
if (document.getElementById('loginForm')) {
    document.getElementById('loginForm').addEventListener('submit', async function(e) {
        e.preventDefault(); // STOP PAGE RELOAD
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        try {
            const response = await fetch(`${API_BASE}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('username', data.username);
                window.location.href = '/'; // Redirect to dashboard
            } else {
                showMessage(data.error || 'Invalid credentials', 'error');
            }
        } catch (error) {
            showMessage('Login failed: ' + error.message, 'error');
        }
    });
}

// --- Load & Display Data ---
async function loadSummary() {
    if(!document.getElementById('cashIn')) return; // Skip if not on dashboard
    
    try {
        const response = await fetch(`${API_BASE}/summary`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('cashIn').textContent = `₹${data.cash_in.toFixed(2)}`;
            document.getElementById('cashOut').textContent = `₹${data.cash_out.toFixed(2)}`;
            document.getElementById('balance').textContent = `₹${data.balance.toFixed(2)}`;
            
            // Update month labels if they exist
            if(document.getElementById('currentMonthDisplay')) 
                document.getElementById('currentMonthDisplay').textContent = data.month_name;
            if(document.getElementById('currentMonthDisplay2'))
                document.getElementById('currentMonthDisplay2').textContent = data.month_name;
        }
    } catch (error) { console.error('Summary error:', error); }
}

async function loadTransactions() {
    if(!document.getElementById('transactionsBody')) return; // Skip if not on dashboard

    try {
        const response = await fetch(`${API_BASE}/transactions`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (response.ok) {
            const data = await response.json();
            // SLICE to show only last 5
            displayTransactions(data.transactions.slice(0, 5));
        }
    } catch (error) { console.error('Trans error:', error); }
}

function displayTransactions(transactions) {
    const tbody = document.getElementById('transactionsBody');
    if(!tbody) return;
    tbody.innerHTML = '';
    
    if(transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 20px; color: #aaa;">No recent transactions</td></tr>';
        return;
    }

    transactions.forEach(t => {
        const row = document.createElement('tr');
        const dateObj = new Date(t.date);
        const dateStr = dateObj.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
        
        row.innerHTML = `
            <td>${dateStr} <small style="color:#999">${dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</small></td>
            <td><span class="type-badge type-${t.type.toLowerCase()}">${t.type}</span></td>
            <td style="font-weight:600">₹${t.amount.toFixed(2)}</td>
            <td>${t.category}</td>
            <td>${t.bank_cash}</td>
            <td style="color: #666; font-size: 0.85rem;">${t.remark || '-'}</td>
            <td>
                <button onclick="openEditModal('${t.transaction_id}')" class="btn-secondary small-btn"><i class="fa-solid fa-pen"></i></button>
                <button onclick="deleteTransaction('${t.transaction_id}')" class="btn-danger small-btn"><i class="fa-solid fa-trash"></i></button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// --- Add Transaction ---
document.getElementById('transactionForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    // Get value from checked radio button
    const type = document.querySelector('input[name="type"]:checked').value;
    
    const transaction = {
        date: document.getElementById('date').value,
        type: type,
        amount: document.getElementById('amount').value,
        category: document.getElementById('category').value,
        bank_cash: document.getElementById('bankCash').value,
        remark: document.getElementById('remark').value
    };

    const res = await fetch(`${API_BASE}/transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(transaction)
    });

    if (res.ok) {
        // Reset form but keep date current
        this.reset();
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        document.getElementById('date').value = now.toISOString().slice(0, 16);
        // Reset type to IN
        document.getElementById('typeIn').checked = true; 
        
        loadTransactions();
        loadSummary();
        showMessage('Added!', 'success');
    } else {
        showMessage('Error adding transaction', 'error');
    }
});

// --- Edit & Delete ---
async function deleteTransaction(id) {
    if(confirm('Delete this transaction?')) {
        const res = await fetch(`${API_BASE}/transactions/${id}`, {
            method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` }
        });
        if(res.ok) { loadTransactions(); loadSummary(); showMessage('Deleted.', 'success'); }
    }
}

// Edit Logic
async function openEditModal(id) {
    const res = await fetch(`${API_BASE}/transactions`, { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await res.json();
    const t = data.transactions.find(x => x.transaction_id == id); 
    
    if(t) {
        document.getElementById('editTransactionId').value = t.transaction_id;
        
        const dateObj = new Date(t.date);
        dateObj.setMinutes(dateObj.getMinutes() - dateObj.getTimezoneOffset());
        document.getElementById('editDate').value = dateObj.toISOString().slice(0, 16);
        
        document.getElementById('editType').value = t.type;
        document.getElementById('editAmount').value = t.amount;
        document.getElementById('editCategory').value = t.category;
        document.getElementById('editBankCash').value = t.bank_cash;
        document.getElementById('editRemark').value = t.remark;
        
        document.getElementById('editModal').style.display = 'block';
    }
}

document.getElementById('editTransactionForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const id = document.getElementById('editTransactionId').value;
    const body = {
        date: document.getElementById('editDate').value,
        type: document.getElementById('editType').value,
        amount: document.getElementById('editAmount').value,
        category: document.getElementById('editCategory').value,
        bank_cash: document.getElementById('editBankCash').value,
        remark: document.getElementById('editRemark').value
    };

    const res = await fetch(`${API_BASE}/transactions/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(body)
    });

    if (res.ok) {
        document.getElementById('editModal').style.display = 'none';
        loadTransactions();
        loadSummary();
        showMessage('Updated!', 'success');
    }
});

// --- Import/Export ---
function toggleImportExport() {
    const panel = document.getElementById('importExportPanel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
}

async function importData() {
    const fileInput = document.getElementById('importFile');
    const file = fileInput.files[0];
    if(!file) { alert("Select a file first"); return; }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/import`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        const data = await res.json();
        if(res.ok) {
            showMessage(data.message, 'success');
            loadTransactions();
            loadSummary();
            fileInput.value = ''; 
        } else {
            alert(data.error || 'Import failed');
        }
    } catch(e) { console.error(e); alert("Import error"); }
}

async function exportToExcel() {
    try {
        const response = await fetch(`${API_BASE}/transactions`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (response.ok) {
            const data = await response.json();
            let csvContent = "Date,Type,Amount,Category,Remark,Bank/Cash\n";
            data.transactions.forEach(t => {
                 csvContent += `${t.date},${t.type},${t.amount},${t.category},${t.remark},${t.bank_cash}\n`;
            });
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.setAttribute("href", url);
            link.setAttribute("download", "cashbook_export.csv"); 
            document.body.appendChild(link); link.click(); document.body.removeChild(link);
        }
    } catch (e) { console.error(e); }
}
async function exportToCSV() { exportToExcel(); } 
function printTable() { window.print(); }

// --- Utils ---
function showMessage(msg, type) {
    const m = document.getElementById('message');
    if(m) {
        m.textContent = msg;
        m.className = `message ${type}`;
        m.style.display = 'block';
        setTimeout(() => m.style.display = 'none', 3000);
    } else {
        alert(msg);
    }
}

function logout() {
    localStorage.clear();
    window.location.href = '/login';
}

function goToDashboard() { window.location.href = '/dashboard'; }

async function loadDropdowns() {
    try {
        const catRes = await fetch(`${API_BASE}/categories`, { headers: { 'Authorization': `Bearer ${token}` } });
        const bankRes = await fetch(`${API_BASE}/banks`, { headers: { 'Authorization': `Bearer ${token}` } });
        if(catRes.ok) {
            const cats = await catRes.json();
            if(document.getElementById('categoryList'))
                document.getElementById('categoryList').innerHTML = cats.map(c => `<option value="${c}">`).join('');
        }
        if(bankRes.ok) {
            const banks = await bankRes.json();
            if(document.getElementById('bankList'))
                document.getElementById('bankList').innerHTML = banks.map(b => `<option value="${b}">`).join('');
        }
    } catch(e) {}
}

// Close Modal Logic
const closeBtn = document.querySelector('.close');
if(closeBtn) closeBtn.onclick = () => document.getElementById('editModal').style.display = 'none';
window.onclick = (e) => { if(e.target == document.getElementById('editModal')) document.getElementById('editModal').style.display = 'none'; }
