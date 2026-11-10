/**
 * Sales Data Analysis System - Client Scripts
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Auto-dismiss / close flash alert buttons
    document.querySelectorAll('.alert-close').forEach(function (button) {
        button.addEventListener('click', function () {
            var alertBox = this.closest('.alert');
            if (alertBox) {
                alertBox.style.opacity = '0';
                setTimeout(function () {
                    alertBox.remove();
                }, 200);
            }
        });
    });

    // 2. Real-time dynamic Revenue calculation on Add/Edit Sale forms
    var qtyInput = document.getElementById('quantity');
    var priceInput = document.getElementById('unit_price');
    var revPreview = document.getElementById('revenue-preview');

    function updateCalculatedRevenue() {
        if (!qtyInput || !priceInput || !revPreview) return;
        var qty = parseFloat(qtyInput.value) || 0;
        var price = parseFloat(priceInput.value) || 0;
        var total = (qty * price).toFixed(2);
        revPreview.textContent = '$' + Number(total).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    if (qtyInput && priceInput) {
        qtyInput.addEventListener('input', updateCalculatedRevenue);
        priceInput.addEventListener('input', updateCalculatedRevenue);
        updateCalculatedRevenue();
    }

    // 3. Confirm sale deletion
    document.querySelectorAll('.form-delete-sale').forEach(function (form) {
        form.addEventListener('submit', function (e) {
            var confirmed = confirm('Are you sure you want to delete this sale record? This action cannot be undone.');
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });

    // 4. File input filename indicator
    var fileInput = document.getElementById('csv_file');
    var fileLabel = document.getElementById('file-chosen-text');
    if (fileInput && fileLabel) {
        fileInput.addEventListener('change', function () {
            if (this.files && this.files.length > 0) {
                fileLabel.textContent = 'Selected: ' + this.files[0].name + ' (' + (this.files[0].size / 1024).toFixed(1) + ' KB)';
            } else {
                fileLabel.textContent = 'No file chosen';
            }
        });
    }
});

// Helper to create charts with Chart.js
function initDashboardCharts(data) {
    if (!data || !data.has_data) return;

    // Palette
    var primaryPurple = '#6366f1';
    var deepPurple = '#4338ca';
    var cyanBlue = '#06b6d4';
    var emerald = '#10b981';
    var amber = '#f59e0b';
    var pink = '#ec4899';
    var palette = [
        '#6366f1', '#3b82f6', '#06b6d4', '#10b981', 
        '#f59e0b', '#ec4899', '#8b5cf6', '#14b8a6', '#f97316'
    ];

    // 1. Monthly Sales Trend (Line Chart)
    var trendEl = document.getElementById('monthlyTrendChart');
    if (trendEl && data.monthly_trend && data.monthly_trend.labels.length > 0) {
        new Chart(trendEl.getContext('2d'), {
            type: 'line',
            data: {
                labels: data.monthly_trend.labels,
                datasets: [{
                    label: 'Monthly Revenue ($)',
                    data: data.monthly_trend.revenues,
                    borderColor: '#4f46e5',
                    backgroundColor: 'rgba(99, 102, 241, 0.15)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.35,
                    pointBackgroundColor: '#4f46e5',
                    pointBorderColor: '#ffffff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return 'Revenue: $' + ctx.parsed.y.toLocaleString();
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (val) { return '$' + val.toLocaleString(); }
                        },
                        grid: { color: '#f1f0f9' }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // 2. Category Sales (Donut/Pie Chart)
    var catEl = document.getElementById('categorySalesChart');
    if (catEl && data.category_sales && data.category_sales.labels.length > 0) {
        new Chart(catEl.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: data.category_sales.labels,
                datasets: [{
                    data: data.category_sales.revenues,
                    backgroundColor: palette,
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { boxWidth: 12, font: { size: 11 } }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                var val = ctx.parsed;
                                var total = ctx.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                                var pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                return ' ' + ctx.label + ': $' + val.toLocaleString() + ' (' + pct + '%)';
                            }
                        }
                    }
                },
                cutout: '62%'
            }
        });
    }

    // 3. Product-wise Sales (Horizontal Bar Chart)
    var prodEl = document.getElementById('productSalesChart');
    if (prodEl && data.product_sales && data.product_sales.labels.length > 0) {
        new Chart(prodEl.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.product_sales.labels,
                datasets: [{
                    label: 'Revenue ($)',
                    data: data.product_sales.revenues,
                    backgroundColor: '#6366f1',
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) { return 'Revenue: $' + ctx.parsed.x.toLocaleString(); }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (val) { return '$' + val.toLocaleString(); }
                        },
                        grid: { color: '#f1f0f9' }
                    },
                    y: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    // 4. Region-wise Sales (Horizontal Bar Chart)
    var regEl = document.getElementById('regionSalesChart');
    if (regEl && data.region_sales && data.region_sales.labels.length > 0) {
        new Chart(regEl.getContext('2d'), {
            type: 'bar',
            data: {
                labels: data.region_sales.labels,
                datasets: [{
                    label: 'Revenue ($)',
                    data: data.region_sales.revenues,
                    backgroundColor: '#8b5cf6',
                    borderRadius: 6,
                    borderSkipped: false
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) { return 'Revenue: $' + ctx.parsed.x.toLocaleString(); }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            callback: function (val) { return '$' + val.toLocaleString(); }
                        },
                        grid: { color: '#f1f0f9' }
                    },
                    y: {
                        grid: { display: false }
                    }
                }
            }
        });
    }
}
