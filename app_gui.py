"""
====================================================================
 Sales Data Analysis System - Pure Python Desktop GUI Application
 Built with: Python 3, Tkinter, Matplotlib, Pandas, NumPy, SQLite3
 ZERO HTML / ZERO BROWSER - 100% Native Python Application
====================================================================
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import pandas as pd
import numpy as np

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Database File Path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sales_data.db')

def init_sqlite_db():
    """Initializes SQLite database tables directly in Python."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        UNIQUE(product_name, category)
    );
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        sale_date DATE NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        customer TEXT NOT NULL,
        region TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    );
    """)
    conn.commit()
    conn.close()

def get_or_create_product(conn, name, category):
    name = str(name).strip()
    category = str(category).strip()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id FROM products WHERE product_name = ? AND category = ? LIMIT 1", (name, category))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute("INSERT INTO products (product_name, category) VALUES (?, ?)", (name, category))
    conn.commit()
    return cursor.lastrowid

def load_sales_dataframe():
    """Loads all sales data from SQLite into a Pandas DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    query = """
    SELECT 
        s.sale_id,
        s.sale_date,
        s.quantity,
        s.unit_price,
        (s.quantity * s.unit_price) AS revenue,
        s.customer,
        s.region,
        p.product_name,
        p.category
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    ORDER BY s.sale_date DESC
    """
    try:
        df = pd.read_sql_query(query, conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    if not df.empty:
        df['sale_date'] = pd.to_datetime(df['sale_date'], errors='coerce')
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
        df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0.0)
        df['revenue'] = df['quantity'] * df['unit_price']
    return df

class SalesAnalysisApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sales Data Analysis System (Python + SQLite)")
        self.geometry("1180x820")
        self.minsize(1000, 700)
        self.configure(bg="#f4f3fb")

        # Color Palette
        self.c_navy = "#1e1b4b"
        self.c_purple = "#4338ca"
        self.c_accent = "#6366f1"
        self.c_bg = "#f4f3fb"
        self.c_white = "#ffffff"
        self.c_green = "#059669"
        self.c_gray = "#64748b"

        # Initialize DB
        init_sqlite_db()

        self.current_filename = None
        self.build_ui()
        self.refresh_dashboard()

    def build_ui(self):
        # Top Header Frame
        header = tk.Frame(self, bg=self.c_navy, height=75)
        header.pack(side="top", fill="x")

        title_lbl = tk.Label(
            header, 
            text="📊 Sales Data Analysis System", 
            font=("Segoe UI", 18, "bold"), 
            bg=self.c_navy, 
            fg="#ffffff"
        )
        title_lbl.pack(side="left", padx=20, pady=(12, 0))

        sub_lbl = tk.Label(
            header, 
            text="Pure Python & SQLite Desktop Analytics Engine • Pandas • Matplotlib", 
            font=("Segoe UI", 9), 
            bg=self.c_navy, 
            fg="#c7d2fe"
        )
        sub_lbl.pack(side="left", padx=20, pady=(0, 12))

        # Toolbar Frame
        toolbar = tk.Frame(self, bg="#ffffff", height=50, bd=1, relief="solid")
        toolbar.pack(side="top", fill="x", padx=15, pady=(10, 5))

        btn_upload = tk.Button(
            toolbar, 
            text="📂 Upload CSV File", 
            font=("Segoe UI", 10, "bold"),
            bg=self.c_purple, 
            fg="#ffffff", 
            activebackground="#312e81", 
            activeforeground="#ffffff",
            padx=12, pady=5, 
            relief="flat", 
            cursor="hand2",
            command=self.upload_csv_dialog
        )
        btn_upload.pack(side="left", padx=10, pady=8)

        btn_sample = tk.Button(
            toolbar, 
            text="📥 Load Sample Data", 
            font=("Segoe UI", 9, "bold"),
            bg="#3b82f6", 
            fg="#ffffff", 
            padx=10, pady=5, 
            relief="flat", 
            cursor="hand2",
            command=self.load_sample_csv
        )
        btn_sample.pack(side="left", padx=5, pady=8)

        btn_table = tk.Button(
            toolbar, 
            text="📋 View Sales Table", 
            font=("Segoe UI", 9, "bold"),
            bg="#f1f5f9", 
            fg="#1e293b", 
            padx=10, pady=5, 
            relief="groove", 
            cursor="hand2",
            command=self.open_records_window
        )
        btn_table.pack(side="left", padx=5, pady=8)

        btn_reset = tk.Button(
            toolbar, 
            text="🔄 Reset / Clear Data", 
            font=("Segoe UI", 9, "bold"),
            bg="#ef4444", 
            fg="#ffffff", 
            padx=10, pady=5, 
            relief="flat", 
            cursor="hand2",
            command=self.reset_data
        )
        btn_reset.pack(side="left", padx=5, pady=8)

        self.status_lbl = tk.Label(
            toolbar, 
            text="No file uploaded yet. Click 'Upload CSV File' to start.", 
            font=("Segoe UI", 9, "italic"),
            bg="#ffffff", 
            fg=self.c_gray
        )
        self.status_lbl.pack(side="right", padx=15, pady=8)

        # KPI Cards Frame
        self.kpi_frame = tk.Frame(self, bg=self.c_bg)
        self.kpi_frame.pack(side="top", fill="x", padx=15, pady=5)

        self.kpi_labels = {}
        kpi_defs = [
            ("sales", "💰 Total Sales", "$0.00"),
            ("quantity", "📦 Total Quantity", "0"),
            ("average", "📊 Average Sale", "$0.00"),
            ("product", "🏆 Best Product", "N/A"),
            ("growth", "📈 Sales Growth", "N/A"),
            ("region", "🌍 Best Region", "N/A"),
        ]

        for idx, (key, title, default_val) in enumerate(kpi_defs):
            card = tk.Frame(self.kpi_frame, bg="#ffffff", bd=1, relief="solid")
            card.pack(side="left", fill="both", expand=True, padx=4, pady=4)

            t_lbl = tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), bg="#ffffff", fg=self.c_gray)
            t_lbl.pack(anchor="w", padx=10, pady=(6, 2))

            v_lbl = tk.Label(card, text=default_val, font=("Segoe UI", 13, "bold"), bg="#ffffff", fg=self.c_navy)
            v_lbl.pack(anchor="w", padx=10, pady=(0, 6))

            self.kpi_labels[key] = v_lbl

        # Charts Area Frame
        self.chart_container = tk.Frame(self, bg="#ffffff", bd=1, relief="solid")
        self.chart_container.pack(side="top", fill="both", expand=True, padx=15, pady=(5, 15))

    def upload_csv_dialog(self):
        file_path = filedialog.askopenfilename(
            title="Select Sales CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if file_path:
            self.process_csv_import(file_path)

    def load_sample_csv(self):
        sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sample_sales.csv')
        if os.path.exists(sample_path):
            self.process_csv_import(sample_path)
        else:
            messagebox.showerror("Error", f"Sample CSV file not found at: {sample_path}")

    def process_csv_import(self, file_path):
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to read CSV file:\n{e}")
            return

        # Check required columns
        req_cols = ['product_name', 'category', 'sale_date', 'quantity', 'unit_price', 'customer', 'region']
        missing = [c for c in req_cols if c.lower() not in [col.lower() for col in df.columns]]
        if missing:
            messagebox.showerror("Invalid CSV", f"Missing required columns:\n{', '.join(missing)}")
            return

        # Standardize column names
        col_map = {c.lower(): c for c in df.columns}
        renamed = pd.DataFrame()
        for c in req_cols:
            renamed[c] = df[col_map[c.lower()]]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Clear old sales to show the dashboard of this file
        cursor.execute("DELETE FROM sales;")
        conn.commit()

        imported_count = 0
        skipped = 0

        for _, row in renamed.iterrows():
            try:
                prod_name = str(row['product_name']).strip()
                cat = str(row['category']).strip()
                sale_date = str(row['sale_date']).strip()
                qty = int(float(row['quantity']))
                price = float(row['unit_price'])
                cust = str(row['customer']).strip()
                reg = str(row['region']).strip()

                if qty <= 0 or price < 0 or not prod_name or not cust:
                    skipped += 1
                    continue

                prod_id = get_or_create_product(conn, prod_name, cat)
                cursor.execute("""
                INSERT INTO sales (product_id, sale_date, quantity, unit_price, customer, region)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (prod_id, sale_date, qty, price, cust, reg))
                imported_count += 1
            except Exception:
                skipped += 1

        conn.commit()
        conn.close()

        self.current_filename = os.path.basename(file_path)
        msg = f"Successfully loaded '{self.current_filename}'!\nImported {imported_count} sales transactions."
        if skipped > 0:
            msg += f"\n({skipped} invalid rows skipped)"
        messagebox.showinfo("Import Success", msg)

        self.status_lbl.config(
            text=f"📁 Active File: {self.current_filename} ({imported_count} records)", 
            fg="#059669", 
            font=("Segoe UI", 9, "bold")
        )
        self.refresh_dashboard()

    def reset_data(self):
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to clear the sales data and reset the dashboard?"):
            conn = sqlite3.connect(DB_PATH)
            conn.cursor().execute("DELETE FROM sales;")
            conn.commit()
            conn.close()
            self.current_filename = None
            self.status_lbl.config(text="No file uploaded. Click 'Upload CSV File' to start.", fg=self.c_gray, font=("Segoe UI", 9, "italic"))
            self.refresh_dashboard()

    def refresh_dashboard(self):
        df = load_sales_dataframe()

        # Clear existing charts in container
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        if df.empty:
            # Set KPIs to zero
            self.kpi_labels['sales'].config(text="$0.00")
            self.kpi_labels['quantity'].config(text="0")
            self.kpi_labels['average'].config(text="$0.00")
            self.kpi_labels['product'].config(text="N/A")
            self.kpi_labels['growth'].config(text="N/A")
            self.kpi_labels['region'].config(text="N/A")

            empty_frame = tk.Frame(self.chart_container, bg="#ffffff")
            empty_frame.pack(expand=True)
            tk.Label(empty_frame, text="📂", font=("Segoe UI", 48), bg="#ffffff").pack(pady=(20, 5))
            tk.Label(empty_frame, text="No Sales Data Loaded Yet", font=("Segoe UI", 16, "bold"), bg="#ffffff", fg=self.c_navy).pack()
            tk.Label(empty_frame, text="Click 'Upload CSV File' or 'Load Sample Data' above to view the dashboard.", font=("Segoe UI", 10), bg="#ffffff", fg=self.c_gray).pack(pady=5)
            return

        # Calculate KPIs using Pandas & NumPy
        total_sales = float(np.sum(df['revenue'].to_numpy()))
        total_qty = int(np.sum(df['quantity'].to_numpy()))
        avg_sale = float(np.mean(df['revenue'].to_numpy()))

        # Best Product
        p_grp = df.groupby('product_name')['revenue'].sum().reset_index()
        best_prod = str(p_grp.sort_values(by='revenue', ascending=False).iloc[0]['product_name']) if not p_grp.empty else 'N/A'

        # Best Region
        r_grp = df.groupby('region')['revenue'].sum().reset_index()
        best_reg = str(r_grp.sort_values(by='revenue', ascending=False).iloc[0]['region']) if not r_grp.empty else 'N/A'

        # Growth MoM
        df['year_month'] = df['sale_date'].dt.to_period('M')
        monthly = df.groupby('year_month')['revenue'].sum().reset_index().sort_values('year_month')
        if len(monthly) >= 2:
            latest = monthly.iloc[-1]['revenue']
            prev = monthly.iloc[-2]['revenue']
            if prev > 0:
                growth_val = ((latest - prev) / prev) * 100.0
                prefix = "+" if growth_val > 0 else ""
                growth_text = f"{prefix}{growth_val:.1f}%"
            else:
                growth_text = "N/A"
        else:
            growth_text = "N/A"

        # Update KPI labels
        self.kpi_labels['sales'].config(text=f"${total_sales:,.2f}")
        self.kpi_labels['quantity'].config(text=f"{total_qty:,}")
        self.kpi_labels['average'].config(text=f"${avg_sale:,.2f}")
        self.kpi_labels['product'].config(text=best_prod)
        self.kpi_labels['growth'].config(text=growth_text)
        self.kpi_labels['region'].config(text=best_reg)

        # Draw 4 Matplotlib Charts
        fig = Figure(figsize=(10, 5.5), dpi=100)
        fig.patch.set_facecolor('#ffffff')

        # 1. Monthly Sales Trend (Top Left)
        ax1 = fig.add_subplot(2, 2, 1)
        x_months = [str(p) for p in monthly['year_month']]
        y_revs = monthly['revenue'].values
        ax1.plot(x_months, y_revs, marker='o', color='#4f46e5', linewidth=2.2, markersize=5)
        ax1.fill_between(x_months, y_revs, color='#6366f1', alpha=0.15)
        ax1.set_title("Monthly Sales Trend ($)", fontsize=10, fontweight='bold', color="#1e1b4b")
        ax1.tick_params(axis='x', rotation=30, labelsize=8)
        ax1.tick_params(axis='y', labelsize=8)
        ax1.grid(True, linestyle='--', alpha=0.5)

        # 2. Category Sales Pie (Top Right)
        ax2 = fig.add_subplot(2, 2, 2)
        cat_grp = df.groupby('category')['revenue'].sum()
        colors = ['#6366f1', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#ec4899']
        ax2.pie(cat_grp.values, labels=cat_grp.index, autopct='%1.1f%%', colors=colors[:len(cat_grp)], startangle=140, textprops={'fontsize': 8})
        ax2.set_title("Category Distribution", fontsize=10, fontweight='bold', color="#1e1b4b")

        # 3. Product Sales Bar (Bottom Left)
        ax3 = fig.add_subplot(2, 2, 3)
        top_prods = df.groupby('product_name')['revenue'].sum().sort_values().tail(6)
        ax3.barh(top_prods.index, top_prods.values, color='#4338ca', height=0.6)
        ax3.set_title("Top Products by Revenue ($)", fontsize=10, fontweight='bold', color="#1e1b4b")
        ax3.tick_params(axis='both', labelsize=8)
        ax3.grid(True, linestyle='--', alpha=0.5, axis='x')

        # 4. Regional Sales Bar (Bottom Right)
        ax4 = fig.add_subplot(2, 2, 4)
        reg_sales = df.groupby('region')['revenue'].sum().sort_values()
        ax4.barh(reg_sales.index, reg_sales.values, color='#7c3aed', height=0.6)
        ax4.set_title("Regional Sales ($)", fontsize=10, fontweight='bold', color="#1e1b4b")
        ax4.tick_params(axis='both', labelsize=8)
        ax4.grid(True, linestyle='--', alpha=0.5, axis='x')

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def open_records_window(self):
        df = load_sales_dataframe()
        if df.empty:
            messagebox.showinfo("Empty", "No sales records to display. Please upload a CSV first.")
            return

        win = tk.Toplevel(self)
        win.title("Sales Records Table")
        win.geometry("900x500")

        cols = ["sale_id", "sale_date", "product_name", "category", "quantity", "unit_price", "revenue", "customer", "region"]
        tree = ttk.Treeview(win, columns=cols, show='headings')

        for col in cols:
            tree.heading(col, text=col.replace('_', ' ').title())
            tree.column(col, width=95, anchor='center')

        scrollbar = ttk.Scrollbar(win, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        tree.pack(fill="both", expand=True)

        for _, row in df.iterrows():
            date_str = str(row['sale_date']).split(' ')[0] if pd.notna(row['sale_date']) else ''
            tree.insert("", "end", values=(
                row['sale_id'],
                date_str,
                row['product_name'],
                row['category'],
                row['quantity'],
                f"${row['unit_price']:,.2f}",
                f"${row['revenue']:,.2f}",
                row['customer'],
                row['region']
            ))

if __name__ == '__main__':
    app = SalesAnalysisApp()
    app.mainloop()
