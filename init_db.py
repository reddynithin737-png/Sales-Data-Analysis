"""
Sales Data Analysis System - Database Initialization Script
Run this script to initialize your database (MySQL or SQLite fallback) and seed sample data.

Usage:
    python init_db.py
"""

import os
import sys
import database

def main():
    print("=" * 60)
    print("Sales Data Analysis System - Database Initialization")
    print("=" * 60)
    
    print("\n[1/3] Initializing Database Schema...")
    try:
        database.init_db()
        db_type = database.get_active_db_type()
        print(f" -> Active Database: {db_type.upper()}")
    except Exception as e:
        print(f" -> Error initializing schema: {e}")
        sys.exit(1)

    # Only seed if --seed flag passed
    if '--seed' in sys.argv:
        print("\n[2/3] Seeding Sample Data (--seed passed)...")
        sample_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'sample_sales.csv')
        if os.path.exists(sample_csv):
            database.seed_sample_sales_if_empty(sample_csv)
    else:
        print("\n[2/3] Skipping auto-seeding sales records (ready for user file upload).")

    print("\n[3/3] Verifying Database Records...")
    try:
        sales_count = database.execute_query("SELECT COUNT(*) as cnt FROM sales", fetchone=True)
        prod_count = database.execute_query("SELECT COUNT(*) as cnt FROM products", fetchone=True)
        user_count = database.execute_query("SELECT COUNT(*) as cnt FROM users", fetchone=True)

        print(f" -> Total Products: {prod_count['cnt'] if prod_count else 0}")
        print(f" -> Total Sales Records: {sales_count['cnt'] if sales_count else 0}")
        print(f" -> Registered Users: {user_count['cnt'] if user_count else 0}")
    except Exception as e:
        print(f" -> Verification error: {e}")

    print("\n" + "=" * 60)
    print("Database initialization complete!")
    print("Start the web app by running: python app.py")
    print("=" * 60)

if __name__ == '__main__':
    main()
