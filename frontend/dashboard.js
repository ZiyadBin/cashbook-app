let categoryChart, incomeExpenseChart, bankChart;

// Load dashboard data
async function loadDashboard() {
    const typeFilter = document.getElementById('typeFilter').value;
    const bankFilter = document.getElementById('bankFilter').value;
    
    try {
        const response = await fetch(`${API_BASE}/dashboard?type=${typeFilter}&bank=${bankFilter}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            updateDashboard(data);
        }
    } catch (error) {
        console.error('Failed to load dashboard:', error);
    }
}

// Update dashboard with data
function updateDashboard(data) {
    // Update summary cards
    document.getElementById('totalBalance').textContent = `$${data.summary.balance.toFixed(2)}`;
    document.getElementById('totalIncome').textContent = `$${data.summary.cash_in.toFixed(2)}`;
    document.getElementById('totalExpenses').textContent = `$${data.summary.cash_out.toFixed(2)}`;
    
    // Update charts
    updateCategoryChart(data.category_breakdown);
    updateIncomeExpenseChart(data.summary);
    updateBankChart(data.bank_breakdown);
    updateCategoryTable(data.category_breakdown);
}

// Category pie chart
function updateCategoryChart(categories) {
    const ctx = document.getElementById('categoryChart').getContext('2d');
    
    if (categoryChart) {
        categoryChart.destroy();
    }
    
    const expenseCategories = categories.filter(cat => cat.type === 'OUT');
    
    categoryChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: expenseCategories.map(cat => cat.category),
            datasets: [{
                data: expenseCategories.map(cat => cat.amount),
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: 'Where Your Money Goes'
                }
            }
        }
    });
}

// Income vs Expense bar chart
function updateIncomeExpenseChart(summary) {
    const ctx = document.getElementById('incomeExpenseChart').getContext('2d');
    
    if (incomeExpenseChart) {
        incomeExpenseChart.destroy();
    }
    
    incomeExpenseChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Income', 'Expenses'],
            datasets: [{
                label: 'Amount ($)',
                data: [summary.cash_in, summary.cash_out],
                backgroundColor: ['#28a745', '#dc3545']
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Bank/Cash chart
function updateBankChart(bankData) {
    const ctx = document.getElementById('bankChart').getContext('2d');
    
    if (bankChart) {
        bankChart.destroy();
    }
    
    bankChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: bankData.map(item => item.bank_cash),
            datasets: [{
                data: bankData.map(item => item.amount),
                backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
            }]
        },
        options: {
            responsive: true
        }
    });
}

// Update category breakdown table
function updateCategoryTable(categories) {
    const tbody = document.getElementById('categoryBody');
    tbody.innerHTML = '';
    
    const total = categories.reduce((sum, cat) => sum + cat.amount, 0);
    
    categories.forEach(category => {
        const percentage = total > 0 ? ((category.amount / total) * 100).toFixed(1) : 0;
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${category.category}</td>
            <td><span class="type-${category.type.toLowerCase()}">${category.type}</span></td>
            <td>${category.bank_cash}</td>
            <td>$${category.amount.toFixed(2)}</td>
            <td>${percentage}%</td>
        `;
        tbody.appendChild(row);
    });
}

// Load bank filter options
async function loadBankFilters() {
    try {
        const response = await fetch(`${API_BASE}/banks`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const banks = await response.json();
            const bankFilter = document.getElementById('bankFilter');
            
            banks.forEach(bank => {
                const option = document.createElement('option');
                option.value = bank;
                option.textContent = bank;
                bankFilter.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load banks:', error);
    }
}

// Navigation
function goToMain() {
    window.location.href = 'index.html';
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    if (!token || !currentUser) {
        window.location.href = 'login.html';
        return;
    }
    
    document.getElementById('usernameDisplay').textContent = `Welcome, ${currentUser}`;
    loadBankFilters();
    loadDashboard();
});
