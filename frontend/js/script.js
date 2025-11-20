const API_BASE = '/api';
let token = localStorage.getItem('token');
let currentUser = localStorage.getItem('username');

document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname === '/login') {
        if (token && currentUser) { window.location.href = '/'; }
    } else {
        if (!token || !currentUser) { window.location.href = '/login'; } 
        else { initializeApp(); }
    }
});

function initializeApp() {
    document.getElementById('usernameDisplay').textContent = `Hi, ${currentUser}`;
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset()); // Local time correction
    if (document.getElementById('date')) {
        document.getElementById('date').value = now.toISOString().slice(0, 16);
    }
    loadTransactions();
    loadSummary();
    loadDropdowns();
}

// --- Load & Display ---
async function loadSummary() {
    try {
        const response = await fetch(`${API_BASE}/summary`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('cashIn').textContent = `₹${data.cash_in.toFixed(2)}`;
            document.getElementById('cashOut').textContent = `₹${data.cash_out.toFixed(2)}`;
            document.getElementById('balance').textContent = `₹${data.balance.toFixed(2)}`;
            
            // Update month labels
            document.getElementById('currentMonthDisplay').textContent = data.month_name;
            document.getElementById('currentMonthDisplay2').textContent = data.month_name;
        }
    } catch (error) { console.error('Summary error:', error); }
}

async function loadTransactions() {
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

// Fixed Edit Logic
async function openEditModal(id) {
    const res = await fetch(`${API_BASE}/transactions`, { headers: { 'Authorization': `Bearer ${token}` } });
    const data = await res.json();
    const t = data.transactions.find(x => x.transaction_id == id); // Loose equality for string/int mismatch
    
    if(t) {
        document.getElementById('editTransactionId').value = t.transaction_id;
        
        // Fix Date format for input
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

// Edit Form Submit
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
            fileInput.value = ''; // clear input
        } else {
            alert(data.error || 'Import failed');
        }
    } catch(e) { console.error(e); alert("Import error"); }
}

// Reuse existing export logic from previous code for exportToExcel/CSV...
// (You can copy paste your previous exportToExcel function here if needed, 
// but the UI now has specific buttons for them calling these names)
async function exportToExcel() {
    // Simple trigger to download all transactions
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
            link.setAttribute("download", "cashbook_export.csv"); // CSV opens in Excel
            document.body.appendChild(link); link.click(); document.body.removeChild(link);
        }
    } catch (e) { console.error(e); }
}
async function exportToCSV() { exportToExcel(); } // Reuse for now

// --- Utils ---
function showMessage(msg, type) {
    const m = document.getElementById('message');
    m.textContent = msg;
    m.className = `message ${type}`;
    m.style.display = 'block';
    setTimeout(() => m.style.display = 'none', 3000);
}

function logout() {
    localStorage.clear();
    window.location.href = '/login';
}

function goToDashboard() { window.location.href = '/dashboard'; }

// Load dropdown helpers
async function loadDropdowns() {
    try {
        const catRes = await fetch(`${API_BASE}/categories`, { headers: { 'Authorization': `Bearer ${token}` } });
        const bankRes = await fetch(`${API_BASE}/banks`, { headers: { 'Authorization': `Bearer ${token}` } });
        if(catRes.ok) {
            const cats = await catRes.json();
            document.getElementById('categoryList').innerHTML = cats.map(c => `<option value="${c}">`).join('');
        }
        if(bankRes.ok) {
            const banks = await bankRes.json();
            document.getElementById('bankList').innerHTML = banks.map(b => `<option value="${b}">`).join('');
        }
    } catch(e) {}
}

// Close Modal Logic
document.querySelector('.close').onclick = () => document.getElementById('editModal').style.display = 'none';
window.onclick = (e) => { if(e.target == document.getElementById('editModal')) document.getElementById('editModal').style.display = 'none'; }
