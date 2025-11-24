let expenseChartInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    loadFullDashboard();
});

async function loadFullDashboard() {
    try {
        const res = await fetch(`${API_BASE}/dashboard`, { 
            headers: { 'Authorization': `Bearer ${token}` } 
        });
        
        if (res.ok) {
            const data = await res.json();
            
            // 1. Animate Numbers
            animateValue('dashIncome', data.summary.total_income);
            animateValue('dashExpense', data.summary.real_expenses);
            animateValue('dashWealth', data.summary.wealth_added);
            animateValue('dashBalance', data.summary.current_balance);

            // 2. Calculate Wealth Rate
            const income = data.summary.total_income;
            const saved = data.summary.wealth_added;
            const rate = income > 0 ? Math.round((saved / income) * 100) : 0;
            
            document.getElementById('wealthPercent').textContent = `${rate}%`;
            document.getElementById('wealthBar').style.width = `${rate}%`;

            // 3. Render Wallet List
            const bankList = document.getElementById('bankBalanceList');
            bankList.innerHTML = '';
            data.bank_chart.forEach(b => {
                const li = document.createElement('li');
                const isPos = b.amount >= 0;
                li.innerHTML = `
                    <span>${b.bank_cash}</span>
                    <span class="bank-amount ${isPos ? 'pos' : 'neg'}">
                        ${isPos ? '+' : ''}₹${b.amount.toLocaleString()}
                    </span>
                `;
                bankList.appendChild(li);
            });

            // 4. Render Chart
            renderChart(data.expense_chart);
        }
    } catch (error) {
        console.error("Dashboard Error:", error);
    }
}

function renderChart(data) {
    const ctx = document.getElementById('expenseChart').getContext('2d');
    
    if (expenseChartInstance) expenseChartInstance.destroy();

    // Sort by amount desc and take top 6, group others
    data.sort((a, b) => b.amount - a.amount);
    
    const labels = data.map(d => d.category);
    const values = data.map(d => d.amount);

    expenseChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    '#6366f1', '#ec4899', '#10b981', '#f59e0b', 
                    '#3b82f6', '#8b5cf6', '#9ca3af'
                ],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { boxWidth: 12, usePointStyle: true } },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.label || '';
                            if (label) label += ': ';
                            label += '₹' + context.raw.toLocaleString();
                            return label;
                        }
                    }
                }
            },
            cutout: '70%', // Makes it a thin ring
        }
    });
}

function animateValue(id, end) {
    const obj = document.getElementById(id);
    if(!obj) return;
    
    const start = 0;
    const duration = 1000;
    let startTimestamp = null;
    
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = Math.floor(progress * (end - start) + start);
        obj.innerHTML = `₹${value.toLocaleString()}`;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}
