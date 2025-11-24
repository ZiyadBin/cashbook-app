let expenseChartInstance = null;
let lendingChartInstance = null;
let allTransactions = [];
let displayedCount = 10;

document.addEventListener('DOMContentLoaded', () => {
    loadFullDashboard();
    loadDropdownsForFilter();
});

async function loadFullDashboard() {
    const type = document.getElementById('typeFilter').value;
    const bank = document.getElementById('bankFilter').value;
    const category = document.getElementById('catFilter').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;

    try {
        // Build URL with params
        const params = new URLSearchParams({
            type: type,
            bank: bank,
            category: category,
            startDate: startDate,
            endDate: endDate
        });

        // 1. Get Analytics Data
        const res = await fetch(`${API_BASE}/dashboard?${params}`, { 
            headers: { 'Authorization': `Bearer ${token}` } 
        });
        
        // 2. Get Full History
        const histRes = await fetch(`${API_BASE}/transactions?${params}`, { 
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
            
            // Update "Money Out" Bar
            document.getElementById('totalMoneyOut').textContent = `₹${data.summary.total_money_out.toLocaleString()}`;
            // Just an animation effect, always full width for visual impact
            document.getElementById('moneyOutBar').style.width = '100%'; 

            // Update Lending Total
            const lentColor = data.summary.lent >= 0 ? '#f59e0b' : '#ef4444';
            document.getElementById('totalLent').style.color = lentColor;
            document.getElementById('totalLent').textContent = `₹${data.summary.lent.toLocaleString()}`;

            // Render Charts
            renderExpenseChart(data.expense_chart);
            renderLendingChart(data.lending_chart);
            renderAssetList(data.asset_chart);

            // Setup Table
            allTransactions = histData.transactions;
            
            // Apply frontend filters to table as well (logic consistency)
            applyFrontendTableFilters(startDate, endDate, category, bank, type);
        }
    } catch (error) {
        console.error("Dashboard Error:", error);
    }
}

function applyFrontendTableFilters(start, end, cat, bank, type) {
    let filtered = allTransactions.filter(t => {
        let valid = true;
        if(type !== 'ALL' && t.type !== type) valid = false;
        if(bank !== 'ALL' && t.bank_cash !== bank) valid = false;
        if(cat !== 'ALL' && t.category !== cat) valid = false;
        
        if(start) {
            if(new Date(t.date) < new Date(start)) valid = false;
        }
        if(end) {
            // End date needs to encompass the full day
            let e = new Date(end); e.setHours(23,59,59);
            if(new Date(t.date) > e) valid = false;
        }
        return valid;
    });
    
    // Reset pagination
    displayedCount = 10;
    renderHistoryTable(filtered);
}

function renderHistoryTable(filteredData) {
    const tbody = document.getElementById('historyBody');
    tbody.innerHTML = '';
    const visibleItems = filteredData.slice(0, displayedCount);

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

    // Handle "Load More" visibility
    const btn = document.getElementById('loadMoreBtn');
    btn.style.display = displayedCount >= filteredData.length ? 'none' : 'block';
    
    // Attach the filtered data to the button so it knows what to load next
    btn.onclick = () => {
        displayedCount += 50;
        renderHistoryTable(filteredData);
    };
}

// --- RENDER ASSETS (New Feature) ---
function renderAssetList(data) {
    const container = document.getElementById('assetList');
    container.innerHTML = '';
    
    if(data.length === 0) {
        container.innerHTML = '<p class="hint-text">No assets found.</p>';
        return;
    }

    // Sort by highest value
    data.sort((a,b) => b.amount - a.amount);
    const maxVal = data[0].amount;

    data.forEach(a => {
        const width = (a.amount / maxVal) * 100;
        const div = document.createElement('div');
        div.className = 'asset-item';
        div.innerHTML = `
            <div class="asset-info">
                <span>${a.category}</span>
                <span class="asset-val">₹${a.amount.toLocaleString()}</span>
            </div>
            <div class="progress-bar">
                <div class="fill purple" style="width: ${width}%"></div>
            </div>
        `;
        container.appendChild(div);
    });
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

    // Color logic: Red if negative (you owe them), Yellow if positive (they owe you)
    const colors = data.map(d => d.amount >= 0 ? '#f59e0b' : '#ef4444');

    lendingChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.person),
            datasets: [{
                data: data.map(d => d.amount),
                backgroundColor: colors,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: { x: { grid: { display: false } } }
        }
    });
}

// --- FILTER DROPDOWNS ---
async function loadDropdownsForFilter() {
    try {
        const bankRes = await fetch(`${API_BASE}/banks`, { headers: { 'Authorization': `Bearer ${token}` } });
        const catRes = await fetch(`${API_BASE}/categories`, { headers: { 'Authorization': `Bearer ${token}` } });
        
        if(bankRes.ok) {
            const banks = await bankRes.json();
            const bFilter = document.getElementById('bankFilter');
            banks.forEach(b => bFilter.innerHTML += `<option value="${b}">${b}</option>`);
        }
        if(catRes.ok) {
            const cats = await catRes.json();
            const cFilter = document.getElementById('catFilter');
            cats.forEach(c => cFilter.innerHTML += `<option value="${c}">${c}</option>`);
        }
    } catch(e) {}
}

function resetFilters() {
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    document.getElementById('typeFilter').value = 'ALL';
    document.getElementById('bankFilter').value = 'ALL';
    document.getElementById('catFilter').value = 'ALL';
    loadFullDashboard();
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
        await fetch(`${API_BASE}/transactions/${box.value}`, { 
            method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } 
        });
    }
    loadFullDashboard();
    document.getElementById('bulkActions').style.display = 'none';
    document.getElementById('selectAll').checked = false;
}

function animateValue(id, end) {
    const obj = document.getElementById(id);
    if(!obj) return;
    obj.innerHTML = `₹${end.toLocaleString()}`;
}
