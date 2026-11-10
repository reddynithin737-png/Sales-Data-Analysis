import os
import sqlite3
import pymysql
import pymysql.cursors
import pandas as pd
from config import Config

# Track active database type ('mysql' or 'sqlite')
_ACTIVE_DB_TYPE = None
_DB_ERROR_MESSAGE = None

def get_active_db_type():
    global _ACTIVE_DB_TYPE
    if _ACTIVE_DB_TYPE is None:
        init_db()
    return _ACTIVE_DB_TYPE

def get_db_error_message():
    return _DB_ERROR_MESSAGE

def get_mysql_connection(select_db=True):
    """Establishes connection to MySQL server using credentials from Config."""
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME if select_db else None,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
    return conn

def get_sqlite_connection():
    """Fallback SQLite database connection."""
    db_path = Config.SQLITE_DB_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_connection():
    """Returns an active database connection based on configured/detected DB type."""
    db_type = get_active_db_type()
    if db_type == 'mysql':
        return get_mysql_connection(select_db=True)
    else:
        return get_sqlite_connection()

def init_db():
    """Initializes database schema and seed products (SQLite primary)."""
    global _ACTIVE_DB_TYPE, _DB_ERROR_MESSAGE

    target_type = Config.DB_TYPE.lower()

    # SQLite is the primary database
    if target_type in ('sqlite', 'auto'):
        _ACTIVE_DB_TYPE = 'sqlite'
        _DB_ERROR_MESSAGE = None
        conn = get_sqlite_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Backward-compatible column migration
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except Exception:
            pass

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
            user_id INTEGER NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
        );
        """)

        sample_products = [
            (1, 'Laptop', 'Electronics'),
            (2, 'Car', 'Automobile'),
            (3, 'Office Desk', 'Furniture'),
            (4, 'Ergonomic Chair', 'Furniture'),
            (5, 'Executive Pen', 'Stationery'),
            (6, 'Gaming Keyboard', 'Electronics'),
            (7, 'Wireless Headphones', 'Electronics'),
            (8, 'Smartwatch', 'Electronics'),
            (9, '4K Monitor', 'Electronics'),
            (10, 'Bluetooth Earbuds', 'Electronics')
        ]
        for p_id, p_name, p_cat in sample_products:
            cursor.execute("""
            INSERT OR IGNORE INTO products (product_id, product_name, category)
            VALUES (?, ?, ?)
            """, (p_id, p_name, p_cat))

        # Seed standard default users (essential for cloud platforms like Vercel)
        from werkzeug.security import generate_password_hash
        default_users = [
            (1, 'Administrator', 'admin@example.com', 'admin', generate_password_hash('admin123'), 'admin'),
            (2, 'L BARDRINATH', 'badri@gmail.com', 'badri', generate_password_hash('password123'), 'user'),
            (3, 'Demo User', 'demo@example.com', 'demo', generate_password_hash('demo123'), 'user')
        ]
        for u_id, u_name, u_email, u_user, u_hash, u_role in default_users:
            cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, full_name, email, username, password_hash, role)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (u_id, u_name, u_email, u_user, u_hash, u_role))
            if u_role == 'admin':
                cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")

        # Auto-seed initial sales records on Vercel so the cloud dashboard is populated
        if os.getenv('VERCEL'):
            sample_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sample_sales.csv')
            if os.path.exists(sample_csv):
                try:
                    import pandas as pd
                    df_sample = pd.read_csv(sample_csv)
                    for _, srow in df_sample.iterrows():
                        cursor.execute("""
                        INSERT OR IGNORE INTO sales (sale_id, sale_date, product_id, quantity, unit_price, customer, region, user_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            int(srow['sale_id']),
                            str(srow['sale_date']),
                            int(srow['product_id']),
                            int(srow['quantity']),
                            float(srow['unit_price']),
                            str(srow['customer']),
                            str(srow['region']),
                            1
                        ))
                except Exception as _se:
                    print(f"[Warning] Auto-seed sales on Vercel: {_se}")

        conn.commit()
        conn.close()
        print("[Database] SQLite database active (sales_data.db)")
        return

    # Optional MySQL configuration if explicitly requested
    if target_type == 'mysql':
        try:
            # Connect to MySQL server without selecting database first to create it
            server_conn = pymysql.connect(
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                charset='utf8mb4',
                autocommit=True
            )
            with server_conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4;")
            server_conn.close()

            # Now connect to the database and create tables
            conn = get_mysql_connection(select_db=True)
            with conn.cursor() as cursor:
                # 1. users table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    full_name VARCHAR(100) NOT NULL,
                    email VARCHAR(100) NOT NULL UNIQUE,
                    username VARCHAR(50) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
                try:
                    cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'")
                except Exception:
                    pass

                # 2. products table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id INT AUTO_INCREMENT PRIMARY KEY,
                    product_name VARCHAR(100) NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    UNIQUE KEY uq_prod_cat (product_name, category)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)

                # 3. sales table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    sale_date DATE NOT NULL,
                    quantity INT NOT NULL,
                    unit_price DECIMAL(10, 2) NOT NULL,
                    customer VARCHAR(100) NOT NULL,
                    region VARCHAR(50) NOT NULL,
                    user_id INT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)

                # Seed initial standard products
                sample_products = [
                    (1, 'Laptop', 'Electronics'),
                    (2, 'Car', 'Automobile'),
                    (3, 'Office Desk', 'Furniture'),
                    (4, 'Ergonomic Chair', 'Furniture'),
                    (5, 'Executive Pen', 'Stationery'),
                    (6, 'Gaming Keyboard', 'Electronics'),
                    (7, 'Wireless Headphones', 'Electronics'),
                    (8, 'Smartwatch', 'Electronics'),
                    (9, '4K Monitor', 'Electronics'),
                    (10, 'Bluetooth Earbuds', 'Electronics')
                ]
                for p_id, p_name, p_cat in sample_products:
                    cursor.execute("""
                    INSERT IGNORE INTO products (product_id, product_name, category)
                    VALUES (%s, %s, %s)
                    """, (p_id, p_name, p_cat))

            conn.close()
            _ACTIVE_DB_TYPE = 'mysql'
            _DB_ERROR_MESSAGE = None
            print("[Database] Connected successfully to MySQL server!")
            return
        except Exception as e:
            _DB_ERROR_MESSAGE = str(e)
            print(f"[Database] MySQL connection attempt failed: {e}")
            raise

def execute_query(sql, params=None, fetchone=False, fetchall=False, commit=False):
    """Executes query on active database with normalized parameter placeholders."""
    if params is None:
        params = ()

    db_type = get_active_db_type()
    conn = get_connection()
    result = None

    try:
        if db_type == 'mysql':
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                if commit:
                    conn.commit()
                if fetchone:
                    result = cursor.fetchone()
                elif fetchall:
                    result = cursor.fetchall()
                elif commit:
                    result = cursor.lastrowid
        else:
            # SQLite uses ? instead of %s
            sqlite_sql = sql.replace('%s', '?')
            cursor = conn.cursor()
            cursor.execute(sqlite_sql, params)
            if commit:
                conn.commit()
            if fetchone:
                row = cursor.fetchone()
                result = dict(row) if row else None
            elif fetchall:
                rows = cursor.fetchall()
                result = [dict(row) for row in rows]
            elif commit:
                result = cursor.lastrowid
    finally:
        conn.close()

    return result

# ----------------- User Queries -----------------

def get_user_by_username(username):
    sql = "SELECT * FROM users WHERE username = %s LIMIT 1"
    return execute_query(sql, (username,), fetchone=True)

def get_user_by_email(email):
    sql = "SELECT * FROM users WHERE email = %s LIMIT 1"
    return execute_query(sql, (email,), fetchone=True)

def get_user_by_id(user_id):
    sql = "SELECT * FROM users WHERE user_id = %s LIMIT 1"
    return execute_query(sql, (user_id,), fetchone=True)

def create_user(full_name, email, username, password_hash, role='user'):
    sql = """
    INSERT INTO users (full_name, email, username, password_hash, role)
    VALUES (%s, %s, %s, %s, %s)
    """
    return execute_query(sql, (full_name, email, username, password_hash, role), commit=True)

def get_all_users_with_stats():
    sql = """
    SELECT 
        u.user_id,
        u.full_name,
        u.email,
        u.username,
        COALESCE(u.role, 'user') AS role,
        u.created_at,
        COUNT(s.sale_id) AS sales_count,
        COALESCE(SUM(s.quantity * s.unit_price), 0) AS total_revenue
    FROM users u
    LEFT JOIN sales s ON u.user_id = s.user_id
    GROUP BY u.user_id, u.full_name, u.email, u.username, u.role, u.created_at
    ORDER BY u.user_id ASC
    """
    return execute_query(sql, fetchall=True)

def delete_user(user_id):
    sql = "DELETE FROM users WHERE user_id = %s"
    return execute_query(sql, (user_id,), commit=True)

def set_user_role(user_id, role):
    sql = "UPDATE users SET role = %s WHERE user_id = %s"
    return execute_query(sql, (role, user_id), commit=True)

def get_system_stats():
    users_cnt = execute_query("SELECT COUNT(*) AS cnt FROM users", fetchone=True)
    sales_cnt = execute_query("SELECT COUNT(*) AS cnt, COALESCE(SUM(quantity * unit_price), 0) AS total_rev, COALESCE(SUM(quantity), 0) AS total_qty FROM sales", fetchone=True)
    prods_cnt = execute_query("SELECT COUNT(*) AS cnt FROM products", fetchone=True)
    return {
        'total_users': users_cnt['cnt'] if users_cnt else 0,
        'total_sales_count': sales_cnt['cnt'] if sales_cnt else 0,
        'total_revenue': float(sales_cnt['total_rev']) if sales_cnt else 0.0,
        'total_quantity': int(sales_cnt['total_qty']) if sales_cnt else 0,
        'total_products': prods_cnt['cnt'] if prods_cnt else 0
    }

def update_user_profile(user_id, full_name, email):
    sql = "UPDATE users SET full_name = %s, email = %s WHERE user_id = %s"
    execute_query(sql, (full_name, email, user_id), commit=True)

def update_user_password(user_id, password_hash):
    sql = "UPDATE users SET password_hash = %s WHERE user_id = %s"
    execute_query(sql, (password_hash, user_id), commit=True)

# ----------------- Product Queries -----------------

def get_all_products():
    sql = "SELECT * FROM products ORDER BY product_name ASC"
    return execute_query(sql, fetchall=True)

def get_all_categories():
    sql = "SELECT DISTINCT category FROM products ORDER BY category ASC"
    rows = execute_query(sql, fetchall=True)
    return [r['category'] for r in rows if r.get('category')]

def get_or_create_product(product_name, category):
    """Finds existing product or inserts a new one, returning product_id."""
    product_name = product_name.strip()
    category = category.strip()
    
    sql = "SELECT product_id FROM products WHERE product_name = %s AND category = %s LIMIT 1"
    row = execute_query(sql, (product_name, category), fetchone=True)
    if row:
        return row['product_id']

    # Insert new product
    ins_sql = "INSERT INTO products (product_name, category) VALUES (%s, %s)"
    new_id = execute_query(ins_sql, (product_name, category), commit=True)
    return new_id

# ----------------- Sales Queries -----------------

def get_all_sales(search=None, category=None, region=None, sort_by=None):
    """Retrieves all sales joined with products, supporting search, filters, and sorting."""
    conditions = []
    params = []

    sql = """
    SELECT 
        s.sale_id,
        s.sale_date,
        s.quantity,
        s.unit_price,
        (s.quantity * s.unit_price) AS revenue,
        s.customer,
        s.region,
        s.product_id,
        p.product_name,
        p.category,
        s.user_id,
        u.username AS added_by
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    LEFT JOIN users u ON s.user_id = u.user_id
    """

    if search:
        search_pattern = f"%{search.strip()}%"
        conditions.append("(p.product_name LIKE %s OR s.customer LIKE %s)")
        params.extend([search_pattern, search_pattern])

    if category:
        conditions.append("p.category = %s")
        params.append(category)

    if region:
        conditions.append("s.region = %s")
        params.append(region)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    # Sorting
    if sort_by == 'date_asc':
        sql += " ORDER BY s.sale_date ASC, s.sale_id ASC"
    elif sort_by == 'revenue_desc':
        sql += " ORDER BY (s.quantity * s.unit_price) DESC"
    elif sort_by == 'revenue_asc':
        sql += " ORDER BY (s.quantity * s.unit_price) ASC"
    elif sort_by == 'quantity_desc':
        sql += " ORDER BY s.quantity DESC"
    else:  # default date_desc
        sql += " ORDER BY s.sale_date DESC, s.sale_id DESC"

    return execute_query(sql, tuple(params), fetchall=True)

def get_sale_by_id(sale_id):
    sql = """
    SELECT 
        s.sale_id,
        s.sale_date,
        s.quantity,
        s.unit_price,
        (s.quantity * s.unit_price) AS revenue,
        s.customer,
        s.region,
        s.product_id,
        p.product_name,
        p.category,
        s.user_id
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    WHERE s.sale_id = %s
    LIMIT 1
    """
    return execute_query(sql, (sale_id,), fetchone=True)

def sale_id_exists(sale_id):
    sql = "SELECT 1 FROM sales WHERE sale_id = %s LIMIT 1"
    row = execute_query(sql, (sale_id,), fetchone=True)
    return row is not None

def insert_sale(sale_date, product_id, quantity, unit_price, customer, region, user_id=None, sale_id=None):
    if sale_id is not None:
        sql = """
        INSERT INTO sales (sale_id, sale_date, product_id, quantity, unit_price, customer, region, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return execute_query(sql, (sale_id, sale_date, product_id, quantity, unit_price, customer, region, user_id), commit=True)
    else:
        sql = """
        INSERT INTO sales (sale_date, product_id, quantity, unit_price, customer, region, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return execute_query(sql, (sale_date, product_id, quantity, unit_price, customer, region, user_id), commit=True)

def update_sale(sale_id, sale_date, product_id, quantity, unit_price, customer, region):
    sql = """
    UPDATE sales
    SET sale_date = %s, product_id = %s, quantity = %s, unit_price = %s, customer = %s, region = %s
    WHERE sale_id = %s
    """
    execute_query(sql, (sale_date, product_id, quantity, unit_price, customer, region, sale_id), commit=True)

def delete_sale(sale_id):
    sql = "DELETE FROM sales WHERE sale_id = %s"
    execute_query(sql, (sale_id,), commit=True)

def get_sales_dataframe():
    """Loads all sales data into a Pandas DataFrame for analysis."""
    rows = get_all_sales()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    if 'sale_date' in df.columns:
        df['sale_date'] = pd.to_datetime(df['sale_date'], errors='coerce')
    if 'quantity' in df.columns:
        df['quantity'] = pd.to_numeric(df['quantity'], errors='coerce').fillna(0).astype(int)
    if 'unit_price' in df.columns:
        df['unit_price'] = pd.to_numeric(df['unit_price'], errors='coerce').fillna(0.0)
    df['revenue'] = df['quantity'] * df['unit_price']
    return df

def seed_sample_sales_if_empty(sample_csv_path, user_id=None):
    """If sales table is empty, auto-seeds from sample CSV so user immediately sees rich data."""
    existing = execute_query("SELECT COUNT(*) as cnt FROM sales", fetchone=True)
    count = existing.get('cnt') if existing else 0
    if count == 0 and os.path.exists(sample_csv_path):
        print("[Database] Sales table is empty. Seeding initial records from sample CSV...")
        try:
            df = pd.read_csv(sample_csv_path)
            for _, row in df.iterrows():
                p_id = get_or_create_product(str(row['product_name']), str(row['category']))
                insert_sale(
                    sale_date=str(row['sale_date']),
                    product_id=p_id,
                    quantity=int(row['quantity']),
                    unit_price=float(row['unit_price']),
                    customer=str(row['customer']),
                    region=str(row['region']),
                    user_id=user_id,
                    sale_id=int(row['sale_id']) if pd.notna(row.get('sale_id')) else None
                )
            print(f"[Database] Successfully seeded {len(df)} initial sales records.")
        except Exception as e:
            print(f"[Database] Error auto-seeding sample data: {e}")
