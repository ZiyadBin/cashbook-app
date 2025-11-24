let expenseChartInstance = null;
let lendingChartInstance = null;
let allTransactions = [];
let displayedCount = 10;

document.addEventListener('DOMContentLoaded', () => {
    loadFullDashboard();
    loadDropdownsForFilter(); // defined in script.js, reusing logic if available or implementing locally
});

async function loadFullDashboard() {
    const typeFilter = document.getElementById('typeFilter').value;
    const bankFilter = document.getElementById('bankFilter').value;

    try {
        // 1. Get Analytics Data
        const res = await fetch(`${API_BASE}/dashboard?type=${typeFilter}&bank=${bankFilter}`, { 
            headers: { 'Authorization': `Bearer ${token}` } 
        });
        
        // 2. Get Full History (We fetch all, then paginate locally for speed)
        const histRes = await fetch(`${API_BASE}/transactions`, { 
            headers: { 'Authorization': `Bearer ${token}` } 
        });

        if (res.ok && histRes.ok) {
            const data = await res.json();
            const histData = await histRes.json();
            
            // Update Metrics
            animateValue('dashIncome', data.summary.income);
            animateValue('dashExpense', data.summary.expenses);
            animateValue('dashAssets', data.summary.assets);
            animateValue('dashBalance', data.summary.balance);
            
            document.getElementById('totalLent').textContent = `₹${data.summary.lent.toLocaleString()}`;

            // Render Charts
            renderExpenseChart(data.expense_chart);
            renderLendingChart(data.lending_chart);

            // Setup Table
            allTransactions = histData.transactions;
            displayedCount = 10; // Reset count on filter change
            renderHistoryTable();
        }
    } catch (error) {
        console.error("Dashboard Error:", error);
    }
}

// --- CHART LOGIC ---
function renderExpenseChart(data) {
    const ctx = document.getElementById('expenseChart').getContext('2d');
    if (expenseChartInstance) expenseChartInstance.destroy();

    data.sort((a, b) => b.amount - a.amount);
    
    expenseChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(d => d.category),
            datasets: [{
                data: data.map(d => d.amount),
                backgroundColor: ['#ef4444', '#f97316', '#f59e0b', '#84cc16', '#06b6d4', '#6366f1', '#d946ef'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'right', labels: { boxWidth: 10 } } },
            cutout: '65%'
        }
    });
}

function renderLendingChart(data) {
    const ctx = document.getElementById('lendingChart').getContext('2d');
    if (lendingChartInstance) lendingChartInstance.destroy();

    lendingChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.person),
            datasets: [{
                label: 'Amount Lent',
                data: data.map(d => d.amount),
                backgroundColor: '#f59e0b',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y', // Horizontal Bar
            plugins: { legend: { display: false } },
            scales: { x: { grid: { display: false } } }
        }
    });
}

// --- TABLE & PAGINATION LOGIC ---
function renderHistoryTable() {
    const tbody = document.getElementById('historyBody');
    tbody.innerHTML = '';
    
    // Filter based on current dashboard selection if needed, 
    // but user requested full history table here.
    // We will apply the filters selected at top to the table too for consistency
    const typeFilter = document.getElementById('typeFilter').value;
    const bankFilter = document.getElementById('bankFilter').value;

    let filtered = allTransactions.filter(t => {
        return (typeFilter === 'ALL' || t.type === typeFilter) &&
               (bankFilter === 'ALL' || t.bank_cash === bankFilter);
    });

    // Slice for pagination
    const visibleItems = filtered.slice(0, displayedCount);

    visibleItems.forEach(t => {
        const tr = document.createElement('tr');
        const dateStr = new Date(t.date).toLocaleDateString('en-IN', {day: '2-digit', month: 'short', year: '2-digit'});
        
        tr.innerHTML = `
            <td><input type="checkbox" class="row-check" value="${t.transaction_id}" onchange="updateBulkState()"></td>
            <td>${dateStr}</td>
            <td><span class="type-badge type-${t.type.toLowerCase()}">${t.type}</span></td>
            <td>${t.category}</td>
            <td>${t.remark || '-'}</td>
            <td>${t.bank_cash}</td>
            <td style="text-align: right; font-weight: 600;">₹${t.amount.toLocaleString()}</td>
            <td style="text-align: center;">
                <button onclick="openEditModal('${t.transaction_id}')" class="btn-secondary small-btn"><i class="fa-solid fa-pen"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    // Hide "Load More" if no more items
    const btn = document.getElementById('loadMoreBtn');
    if (displayedCount >= filtered.length) btn.style.display = 'none';
    else btn.style.display = 'block';
}

function loadMore() {
    displayedCount += 10; // Or 50 as requested
    renderHistoryTable();
}

// --- BULK ACTIONS ---
function toggleSelectAll() {
    const mainCheck = document.getElementById('selectAll');
    const rows = document.querySelectorAll('.row-check');
    rows.forEach(r => r.checked = mainCheck.checked);
    updateBulkState();
}

function updateBulkState() {
    const checked = document.querySelectorAll('.row-check:checked');
    const bar = document.getElementById('bulkActions');
    
    if (checked.length > 0) {
        bar.style.display = 'flex';
        document.getElementById('selectedCount').textContent = `${checked.length} Selected`;
    } else {
        bar.style.display = 'none';
    }
}

async function bulkDelete() {
    const checked = document.querySelectorAll('.row-check:checked');
    if (!confirm(`Delete ${checked.length} transactions? This cannot be undone.`)) return;

    for (const box of checked) {
        const id = box.value;
        await fetch(`${API_BASE}/transactions/${id}`, { 
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` } 
        });
    }
    
    // Refresh
    loadFullDashboard();
    document.getElementById('bulkActions').style.display = 'none';
    document.getElementById('selectAll').checked = false;
    showMessage('Bulk delete successful', 'success');
}

// --- HELPERS ---
function animateValue(id, end) {
    const obj = document.getElementById(id);
    if(!obj) return;
    const start = 0; const duration = 800;
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = `₹${Math.floor(progress * (end - start) + start).toLocaleString()}`;
        if (progress < 1) window.requestAnimationFrame(step);
    };
    window.requestAnimationFrame(step);
}

// Copy of loadDropdowns logic specifically for the filter bar
async function loadDropdownsForFilter() {
    try {
        const bankRes = await fetch(`${API_BASE}/banks`, { headers: { 'Authorization': `Bearer ${token}` } });
        if(bankRes.ok) {
            const banks = await bankRes.json();
            const filter = document.getElementById('bankFilter');
            banks.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b; opt.textContent = b;
                filter.appendChild(opt);
            });
        }
    } catch(e) {}
}
