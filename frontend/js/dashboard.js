let expenseChartInstance = null;
let lendingChartInstance = null;
let moneyOutChartInstance = null;
let allTransactions = [];
let displayedCount = 10;

document.addEventListener('DOMContentLoaded', () => {
    loadFullDashboard();
    loadDropdownsForFilter();
});

async function loadFullDashboard() {
    const params = new URLSearchParams({
        type: document.getElementById('typeFilter').value,
        bank: document.getElementById('bankFilter').value,
        category: document.getElementById('catFilter').value,
        startDate: document.getElementById('startDate').value,
        endDate: document.getElementById('endDate').value
    });

    try {
        const res = await fetch(`${API_BASE}/dashboard?${params}`, { headers: { 'Authorization': `Bearer ${token}` } });
        const histRes = await fetch(`${API_BASE}/transactions?${params}`, { headers: { 'Authorization': `Bearer ${token}` } });

        if (res.ok && histRes.ok) {
            const data = await res.json();
            const histData = await histRes.json();
            
            animateValue('dashIncome', data.summary.income);
            animateValue('dashExpense', data.summary.expenses);
            animateValue('dashAssets', data.summary.assets);
            animateValue('dashBalance', data.summary.balance);
            
            document.getElementById('totalExpenseHeader').textContent = `₹${data.summary.expenses.toLocaleString()}`;
            document.getElementById('totalLentHeader').textContent = `₹${data.summary.lent.toLocaleString()}`;

            renderExpenseChart(data.expense_chart);
            renderLendingChart(data.lending_chart);
            renderMoneyOutChart(data.money_out_chart); // Asset chart removed

            allTransactions = histData.transactions;
            displayedCount = 10;
            renderHistoryTable();
        }
    } catch (error) { console.error(error); }
}

function renderExpenseChart(data) {
    if(!data) return;
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
        options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { position: 'right', labels: { boxWidth: 10 } } } }
    });
}

function renderLendingChart(data) {
    if(!data) return;
    const ctx = document.getElementById('lendingChart').getContext('2d');
    if (lendingChartInstance) lendingChartInstance.destroy();
    
    lendingChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.person),
            datasets: [{
                data: data.map(d => d.amount),
                backgroundColor: data.map(d => d.amount >= 0 ? '#f59e0b' : '#ef4444'),
                borderRadius: 4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } } } }
    });
}

function renderMoneyOutChart(data) {
    if(!data) return;
    const ctx = document.getElementById('moneyOutChart').getContext('2d');
    if (moneyOutChartInstance) moneyOutChartInstance.destroy();
    data.sort((a, b) => b.amount - a.amount);

    moneyOutChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.category),
            datasets: [{
                label: 'Cash Outflow',
                data: data.map(d => d.amount),
                backgroundColor: '#10b981',
                borderRadius: 4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
    });
}

function renderHistoryTable() {
    const tbody = document.getElementById('historyBody');
    tbody.innerHTML = '';
    const visible = allTransactions.slice(0, displayedCount);
    
    visible.forEach(t => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="checkbox" class="row-check" value="${t.transaction_id}" onchange="updateBulk()"></td>
            <td>${new Date(t.date).toLocaleDateString('en-IN')}</td>
            <td><span class="type-badge type-${t.type.toLowerCase()}">${t.type}</span></td>
            <td>${t.category}</td>
            <td>${t.remark || '-'}</td>
            <td>${t.bank_cash}</td>
            <td style="text-align:right">₹${t.amount.toLocaleString()}</td>
            <td style="text-align:center"><button onclick="openEditModal('${t.transaction_id}')" class="btn-secondary small-btn"><i class="fa-solid fa-pen"></i></button></td>
        `;
        tbody.appendChild(tr);
    });
    document.getElementById('loadMoreBtn').style.display = displayedCount >= allTransactions.length ? 'none' : 'block';
}

function loadMore() { displayedCount += 50; renderHistoryTable(); }
function updateBulk() { 
    const c = document.querySelectorAll('.row-check:checked').length;
    document.getElementById('bulkActions').style.display = c > 0 ? 'flex' : 'none';
    document.getElementById('selectedCount').textContent = `${c} Selected`;
}
function toggleSelectAll() {
    const s = document.getElementById('selectAll').checked;
    document.querySelectorAll('.row-check').forEach(c => c.checked = s);
    updateBulk();
}
async function bulkDelete() {
    if(!confirm("Delete selected?")) return;
    const chk = document.querySelectorAll('.row-check:checked');
    for(const c of chk) await fetch(`${API_BASE}/transactions/${c.value}`, { method: 'DELETE', headers: {'Authorization': `Bearer ${token}`} });
    loadFullDashboard();
}
function animateValue(id, end) { document.getElementById(id).innerHTML = `₹${end.toLocaleString()}`; }
async function loadDropdownsForFilter() {
    try {
        const bankRes = await fetch(`${API_BASE}/banks`, { headers: { 'Authorization': `Bearer ${token}` } });
        const catRes = await fetch(`${API_BASE}/categories`, { headers: { 'Authorization': `Bearer ${token}` } });
        if(bankRes.ok) (await bankRes.json()).forEach(b => document.getElementById('bankFilter').innerHTML += `<option value="${b}">${b}</option>`);
        if(catRes.ok) (await catRes.json()).forEach(c => document.getElementById('catFilter').innerHTML += `<option value="${c}">${c}</option>`);
    } catch(e) {}
}
function resetFilters() {
    ['startDate','endDate'].forEach(i=>document.getElementById(i).value='');
    ['typeFilter','bankFilter','catFilter'].forEach(i=>document.getElementById(i).value='ALL');
    loadFullDashboard();
}
