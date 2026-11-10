# 📊 Sales Data Analysis System

A full-stack, beginner-friendly web application built with **Python, Flask, SQLite, Pandas, and Chart.js** designed for managing, validating, analyzing, and visualizing enterprise sales data.

Developed for **B.Tech CSE** academic coursework and practical demonstration.

---

## 🌟 Key Features

1. **Self-Contained SQLite Database**
   - Zero installation or server setup required (`sales_data.db`).
   - Runs out-of-the-box on any Windows, macOS, or Linux machine.
   - Optional MySQL support available via `.env` if desired.

1. **Secure User Authentication**
   - User registration with validation (email format, password length, duplicate prevention)
   - Secure password hashing using Werkzeug (`scrypt`/`pbkdf2`)
   - Flask session-based authentication & route protection (`@login_required`)
   - User profile management & password change

2. **Interactive Analytics Dashboard**
   - **Key Performance Indicators (KPI Cards)**:
     - 💰 **Total Sales**: Overall gross revenue
     - 📦 **Total Quantity**: Total units sold
     - 📊 **Average Sale**: Average transaction revenue
     - 🏆 **Best Product**: Top revenue-generating product
     - 📈 **Sales Growth**: Month-over-month (MoM) growth percentage (shows `"N/A"` if insufficient data)
     - 🌍 **Best Region**: Top performing sales region
   - **Visual Charts**:
     - 📈 Monthly Sales Trend (Line Chart with revenue by month)
     - 🍰 Category Sales Distribution (Donut Chart with percentage shares)
     - 🏆 Product-wise Sales (Horizontal Bar Chart)
     - 🌍 Regional Sales Performance (Horizontal Bar Chart)
   - Friendly empty-state handling when no records exist

3. **Sales Records Management**
   - Full CRUD operations: Create, Read, Update, Delete
   - Live dynamic revenue calculation: `Revenue = Quantity × Price`
   - Real-time search by Product Name or Customer Name
   - Multi-criteria filtering by Category and Region
   - Sorting options (Date newest/oldest, Revenue high/low, Quantity high/low)
   - Styled tables with confirmation modals before deletion

4. **Robust CSV Validation & Import**
   - Batch upload of `.csv` sales records
   - Comprehensive validation before database insertion:
     - Header schema check: `sale_id, product_id, product_name, category, sale_date, quantity, unit_price, customer, region`
     - Valid date parsing
     - Numeric quantity check (`> 0`)
     - Numeric unit price check (`>= 0`)
     - Non-empty field validation
   - **Documented Duplicate Policy**:
     - Pre-existing `sale_id` values in the database are detected and skipped.
     - Duplicates repeated within the uploaded CSV file itself are detected and reported.
   - **Validation Report**:
     - Summary pills: 🟢 Valid Count, 🔴 Invalid Count, 🟡 Duplicate Count
     - Invalid records table with explicit **Error Reason** column
     - Preview table of verified records before committing to the database

5. **Dual-Mode Database Architecture**
   - **Primary**: MySQL Server (`sales_db`) with full foreign keys and relational integrity.
   - **Smart Fallback**: Automatic SQLite fallback if MySQL is not configured yet or temporarily offline, ensuring zero friction for local evaluation and grading.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, Flask 3.x
- **Data Analysis**: Pandas, NumPy
- **Visualizations**: Chart.js (interactive web charts) & Matplotlib (backend chart generation)
- **Database**: MySQL Server 8.0 (PyMySQL / mysql-connector-python)
- **Frontend**: Responsive HTML5, CSS3 (Modern Purple/Blue gradient theme), Vanilla JavaScript

---

## 📁 Project Directory Structure

```text
sales_data_analysis/
│
├── app.py                      # Main Flask application & routes
├── config.py                   # Configuration & environment variables
├── database.py                 # Unified database layer (MySQL + SQLite fallback)
├── analytics.py                # Pandas, NumPy & Matplotlib analytics engine
├── csv_validator.py            # CSV parsing, verification & duplicate detection
├── init_db.py                  # Database setup & sample data seeder
├── test_app.py                 # Automated test suite (all routes & flows)
├── schema.sql                  # MySQL database creation & table DDL
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment configuration
├── .env                        # Local environment configuration
│
├── templates/
│   ├── base.html               # Main layout, nav, alerts & footer
│   ├── login.html              # Sign-in page
│   ├── register.html           # Account registration page
│   ├── dashboard.html          # Main sales analytics dashboard & charts
│   ├── sales_records.html      # Records list with search, filter & sort
│   ├── add_sale.html           # Manual transaction entry with live math
│   ├── edit_sale.html          # Update existing transaction
│   ├── import_csv.html         # CSV upload, validation & error report
│   ├── product_analysis.html   # Product ranking leaderboard & charts
│   ├── region_analysis.html    # Regional distribution breakdown
│   ├── profile.html            # User profile & password reset
│   └── error.html              # 404 and 500 error pages
│
├── static/
│   ├── css/
│   │   └── style.css           # Custom purple-blue gradient stylesheet
│   ├── js/
│   │   └── script.js           # Chart.js initialization & dynamic UI
│   ├── uploads/                # Temporary directory for CSV uploads
│   └── charts/                 # Generated Matplotlib charts
│
├── data/
│   ├── sample_sales.csv        # Realistic 30-record sample dataset
│   └── test_with_errors.csv    # Test dataset with malformed & duplicate rows
│
└── README.md                   # Setup guide and documentation
```

---

## 🚀 Setup & Execution Guide

Follow these steps to run the application on your computer:

### Step 1: Create a Python Virtual Environment (Recommended)

Open your terminal or PowerShell inside the project directory:

```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

---

### Step 2: Install Project Requirements

```bash
pip install -r requirements.txt
```

---

### Step 3: Configure Database Credentials

Open `.env` (or copy `.env.example` to `.env`) and enter your MySQL credentials:

```ini
# .env file
SECRET_KEY=sales-analysis-secret-key-2026

# MySQL Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password_here
DB_NAME=sales_db

# Mode: 'auto' (connects to MySQL if credentials match, else uses SQLite fallback)
DB_TYPE=auto
```

> **Note**: If your local MySQL Server is not yet running or password is blank, the app will automatically run in zero-configuration SQLite mode so you can test immediately without any errors.

---

### Step 4: Initialize the Database (MySQL or SQLite)

Run the initialization script:

```bash
python init_db.py
```

This will:
1. Connect to MySQL (or prepare SQLite).
2. Create the `sales_db` database and all required tables (`users`, `products`, `sales`).
3. Seed standard products and initial 30 sample sales transactions.

Alternatively, if you prefer using **MySQL Workbench**, open `schema.sql` and execute it in MySQL Workbench.

---

### Step 5: Start the Flask Application

```bash
python app.py
```

You should see output similar to:

```text
============================================================
 🚀 Sales Data Analysis System is running!
 📦 Active Database: MYSQL (or SQLITE)
 🌐 Access application at: http://127.0.0.1:5000
============================================================
```

---

### Step 6: Open the Website

Open your browser and navigate to:

👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

### Step 7: Create Your First User & Login

1. Click **"Register"** or **"Create an Account"**.
2. Fill in:
   - **Full Name**: e.g., `Nani Lekkalapudi`
   - **Email**: e.g., `nani@example.com`
   - **Username**: e.g., `nani`
   - **Password**: `password123`
3. Click **"Create Account"**.
4. Log in with your new username and password.

---

### Step 8: Test All Features

1. **Dashboard (`/dashboard`)**:
   - Inspect the 6 KPI cards (Total Sales, Total Quantity, Average Sale, Best Product, Sales Growth, Best Region).
   - Review the Monthly Trend line chart, Category donut chart, and horizontal bar charts.
2. **Sales Records (`/sales`)**:
   - Filter by Category (e.g. `Electronics`) or Region (e.g. `North`).
   - Search by customer name (e.g. `Alice`).
   - Sort by Revenue or Date.
3. **Add New Sale (`/sales/add`)**:
   - Enter a date, product name, quantity, and unit price.
   - Notice the dynamic revenue calculation updating instantly on screen!
   - Click **"Save Sale"** and view the newly created record.
4. **CSV Import & Error Validation (`/import`)**:
   - Click **"Download Sample CSV"** or select `data/sample_sales.csv`.
   - To test validation and error reporting, select `data/test_with_errors.csv`.
   - Review the **Validation Report**: Valid Count, Invalid Count (with specific error explanations), and Duplicate Count.
   - Click **"Confirm & Import Valid Records"** to commit valid entries into the database.
5. **Product & Region Analysis (`/products`, `/regions`)**:
   - View top rankings, horizontal charts, and percentage contribution breakdowns.
6. **Profile Management (`/profile`)**:
   - Update your display name and email.
   - Test password change.
7. **Logout (`/logout`)**:
   - Session is cleared and access to protected pages is restricted.

---

## 🧪 Running Automated Tests

Run the built-in test suite to verify all endpoints, database queries, and validation rules:

```bash
python test_app.py
```

---

## 📋 Database Tables (Relational Design)

### 1. `users` Table
| Column | Type | Description |
|---|---|---|
| `user_id` | INT AUTO_INCREMENT | Primary Key |
| `full_name` | VARCHAR(100) | Full Name |
| `email` | VARCHAR(100) UNIQUE | Email Address |
| `username` | VARCHAR(50) UNIQUE | Login Username |
| `password_hash` | VARCHAR(255) | Secure Password Hash |
| `created_at` | DATETIME | Account timestamp |

### 2. `products` Table
| Column | Type | Description |
|---|---|---|
| `product_id` | INT AUTO_INCREMENT | Primary Key |
| `product_name` | VARCHAR(100) | Name of Product |
| `category` | VARCHAR(100) | Product Category |

### 3. `sales` Table
| Column | Type | Description |
|---|---|---|
| `sale_id` | INT AUTO_INCREMENT | Primary Key |
| `product_id` | INT | Foreign Key (`products.product_id`) |
| `sale_date` | DATE | Date of transaction |
| `quantity` | INT | Units sold |
| `unit_price` | DECIMAL(10,2) | Unit sale price |
| `customer` | VARCHAR(100) | Customer Name |
| `region` | VARCHAR(50) | Sales Territory / Region |
| `user_id` | INT | Foreign Key (`users.user_id`) |
| `created_at` | DATETIME | Insertion timestamp |

---

## 📄 License & Attribution

Designed and created for academic demonstration as a **B.Tech CSE Capstone / Major / Minor Project**.
Feel free to use and extend!
