import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Headless backend for web server
import matplotlib.pyplot as plt
import database

def get_kpis_and_analytics(df=None):
    """
    Computes key performance indicators, summary metrics, and data for charts.
    Uses Pandas and NumPy.
    """
    if df is None or df.empty:
        df = database.get_sales_dataframe()

    if df.empty:
        return {
            'has_data': False,
            'total_sales': 0,
            'total_quantity': 0,
            'avg_sale': 0,
            'best_product': 'N/A',
            'best_product_revenue': 0,
            'best_region': 'N/A',
            'best_region_revenue': 0,
            'sales_growth': 'N/A',
            'sales_growth_positive': True,
            'monthly_trend': {'labels': [], 'revenues': [], 'quantities': []},
            'category_sales': {'labels': [], 'revenues': [], 'percentages': []},
            'product_sales': {'labels': [], 'revenues': [], 'quantities': []},
            'region_sales': {'labels': [], 'revenues': [], 'quantities': []},
            'product_ranking': [],
            'region_ranking': []
        }

    # Clean & ensure numeric types
    df = df.copy()
    df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
    df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0.0)
    df['revenue'] = df['quantity'] * df['unit_price']
    df['sale_date'] = pd.to_datetime(df['sale_date'], errors='coerce')
    df = df.dropna(subset=['sale_date'])

    # KPI 1: Total Sales Revenue
    total_sales = float(np.sum(df['revenue'].to_numpy()))

    # KPI 2: Total Quantity Sold
    total_quantity = int(np.sum(df['quantity'].to_numpy()))

    # KPI 3: Average Sale Value
    avg_sale = float(np.mean(df['revenue'].to_numpy())) if len(df) > 0 else 0.0

    # KPI 4: Best Product
    prod_rev = df.groupby('product_name')['revenue'].sum().reset_index()
    if not prod_rev.empty:
        top_prod_row = prod_rev.sort_values(by='revenue', ascending=False).iloc[0]
        best_product = str(top_prod_row['product_name'])
        best_product_revenue = float(top_prod_row['revenue'])
    else:
        best_product = 'N/A'
        best_product_revenue = 0.0

    # KPI 5: Best Region
    reg_rev = df.groupby('region')['revenue'].sum().reset_index()
    if not reg_rev.empty:
        top_reg_row = reg_rev.sort_values(by='revenue', ascending=False).iloc[0]
        best_region = str(top_reg_row['region'])
        best_region_revenue = float(top_reg_row['revenue'])
    else:
        best_region = 'N/A'
        best_region_revenue = 0.0

    # KPI 6: Sales Growth (Month-over-Month using previous period)
    # Group by Year-Month
    df['year_month'] = df['sale_date'].dt.to_period('M')
    monthly_group = df.groupby('year_month').agg(
        revenue=('revenue', 'sum'),
        quantity=('quantity', 'sum')
    ).reset_index()
    monthly_group = monthly_group.sort_values('year_month')

    sales_growth = "N/A"
    sales_growth_positive = True
    if len(monthly_group) >= 2:
        latest_rev = float(monthly_group.iloc[-1]['revenue'])
        prev_rev = float(monthly_group.iloc[-2]['revenue'])
        if prev_rev > 0:
            growth_val = ((latest_rev - prev_rev) / prev_rev) * 100.0
            sales_growth_positive = growth_val >= 0
            prefix = "+" if growth_val > 0 else ""
            sales_growth = f"{prefix}{growth_val:.1f}%"
        else:
            sales_growth = "N/A"

    # Monthly Trend Data (for line chart)
    monthly_labels = [str(period) for period in monthly_group['year_month']]
    monthly_revenues = [round(float(r), 2) for r in monthly_group['revenue']]
    monthly_quantities = [int(q) for q in monthly_group['quantity']]

    # Category Sales (for Donut / Pie chart)
    cat_group = df.groupby('category')['revenue'].sum().reset_index().sort_values('revenue', ascending=False)
    cat_labels = cat_group['category'].tolist()
    cat_revenues = [round(float(r), 2) for r in cat_group['revenue']]
    cat_percentages = [round((r / total_sales) * 100, 1) if total_sales > 0 else 0 for r in cat_revenues]

    # Product-wise Sales Ranking (for horizontal bar chart & table)
    p_rank = df.groupby(['product_name', 'category']).agg(
        total_quantity=('quantity', 'sum'),
        total_revenue=('revenue', 'sum')
    ).reset_index()
    p_rank = p_rank.sort_values(by='total_revenue', ascending=False)

    product_ranking = []
    for rank_idx, (_, row) in enumerate(p_rank.iterrows(), start=1):
        rev = float(row['total_revenue'])
        qty = int(row['total_quantity'])
        pct = round((rev / total_sales) * 100, 1) if total_sales > 0 else 0.0
        avg_price = round(rev / qty, 2) if qty > 0 else 0.0
        product_ranking.append({
            'rank': rank_idx,
            'product_name': row['product_name'],
            'category': row['category'],
            'quantity': qty,
            'revenue': rev,
            'avg_price': avg_price,
            'percentage': pct
        })

    # Top products for chart (top 8)
    top_p_chart = p_rank.head(8).iloc[::-1]  # reversed for horizontal bar chart
    product_chart_labels = top_p_chart['product_name'].tolist()
    product_chart_revenues = [round(float(r), 2) for r in top_p_chart['total_revenue']]
    product_chart_quantities = [int(q) for q in top_p_chart['total_quantity']]

    # Region-wise Sales Ranking (for horizontal bar chart & table)
    r_rank = df.groupby('region').agg(
        transactions=('sale_id', 'count'),
        total_quantity=('quantity', 'sum'),
        total_revenue=('revenue', 'sum')
    ).reset_index()
    r_rank = r_rank.sort_values(by='total_revenue', ascending=False)

    region_ranking = []
    for rank_idx, (_, row) in enumerate(r_rank.iterrows(), start=1):
        rev = float(row['total_revenue'])
        qty = int(row['total_quantity'])
        pct = round((rev / total_sales) * 100, 1) if total_sales > 0 else 0.0
        region_ranking.append({
            'rank': rank_idx,
            'region': row['region'],
            'transactions': int(row['transactions']),
            'quantity': qty,
            'revenue': rev,
            'percentage': pct
        })

    r_chart = r_rank.iloc[::-1]  # reversed for bottom-up horizontal bar
    region_chart_labels = r_chart['region'].tolist()
    region_chart_revenues = [round(float(r), 2) for r in r_chart['total_revenue']]
    region_chart_quantities = [int(q) for q in r_chart['total_quantity']]

    return {
        'has_data': True,
        'total_sales': round(total_sales, 2),
        'total_quantity': total_quantity,
        'avg_sale': round(avg_sale, 2),
        'best_product': best_product,
        'best_product_revenue': round(best_product_revenue, 2),
        'best_region': best_region,
        'best_region_revenue': round(best_region_revenue, 2),
        'sales_growth': sales_growth,
        'sales_growth_positive': sales_growth_positive,
        'monthly_trend': {
            'labels': monthly_labels,
            'revenues': monthly_revenues,
            'quantities': monthly_quantities
        },
        'category_sales': {
            'labels': cat_labels,
            'revenues': cat_revenues,
            'percentages': cat_percentages
        },
        'product_sales': {
            'labels': product_chart_labels,
            'revenues': product_chart_revenues,
            'quantities': product_chart_quantities
        },
        'region_sales': {
            'labels': region_chart_labels,
            'revenues': region_chart_revenues,
            'quantities': region_chart_quantities
        },
        'product_ranking': product_ranking,
        'region_ranking': region_ranking
    }

def generate_matplotlib_charts(output_dir='static/charts'):
    """
    Generates Matplotlib charts and saves them as PNG files in static/charts/.
    Satisfies curriculum requirement for Matplotlib chart generation.
    """
    os.makedirs(output_dir, exist_ok=True)
    df = database.get_sales_dataframe()
    if df.empty:
        return {}

    generated_files = {}

    # Common styling for Matplotlib: Purple/indigo palette
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # 1. Monthly Sales Trend Line Chart
    df['year_month'] = df['sale_date'].dt.to_period('M')
    monthly = df.groupby('year_month')['revenue'].sum().reset_index().sort_values('year_month')
    
    fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
    x_labels = [str(p) for p in monthly['year_month']]
    y_values = monthly['revenue'].values
    ax.plot(x_labels, y_values, marker='o', linewidth=2.5, color='#6366f1', markersize=6, label='Monthly Revenue ($)')
    ax.fill_between(x_labels, y_values, color='#6366f1', alpha=0.15)
    ax.set_title('Monthly Sales Trend', fontsize=13, fontweight='bold', color='#1e1b4b', pad=12)
    ax.set_xlabel('Month', fontsize=10, fontweight='bold', color='#475569')
    ax.set_ylabel('Revenue ($)', fontsize=10, fontweight='bold', color='#475569')
    plt.xticks(rotation=45, ha='right', fontsize=9)
    plt.tight_layout()
    trend_path = os.path.join(output_dir, 'monthly_trend.png')
    fig.savefig(trend_path)
    plt.close(fig)
    generated_files['monthly_trend'] = trend_path

    # 2. Product-wise Sales Horizontal Bar Chart
    p_rev = df.groupby('product_name')['revenue'].sum().reset_index().sort_values('revenue', ascending=True).tail(8)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    bars = ax.barh(p_rev['product_name'], p_rev['revenue'], color='#4f46e5', height=0.6)
    ax.set_title('Sales by Product', fontsize=13, fontweight='bold', color='#1e1b4b', pad=12)
    ax.set_xlabel('Revenue ($)', fontsize=10, fontweight='bold', color='#475569')
    plt.tight_layout()
    prod_path = os.path.join(output_dir, 'product_sales.png')
    fig.savefig(prod_path)
    plt.close(fig)
    generated_files['product_sales'] = prod_path

    # 3. Regional Sales Horizontal Bar Chart
    r_rev = df.groupby('region')['revenue'].sum().reset_index().sort_values('revenue', ascending=True)
    fig, ax = plt.subplots(figsize=(8, 4), dpi=120)
    ax.barh(r_rev['region'], r_rev['revenue'], color='#7c3aed', height=0.55)
    ax.set_title('Regional Sales Performance', fontsize=13, fontweight='bold', color='#1e1b4b', pad=12)
    ax.set_xlabel('Revenue ($)', fontsize=10, fontweight='bold', color='#475569')
    plt.tight_layout()
    reg_path = os.path.join(output_dir, 'region_sales.png')
    fig.savefig(reg_path)
    plt.close(fig)
    generated_files['region_sales'] = reg_path

    return generated_files
