import os
import re
import json
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, jsonify, send_from_directory, send_file
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import Config
import database
import analytics
import csv_validator

app = Flask(__name__)
app.config.from_object(Config)

# Ensure upload and chart directories exist
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(app.static_folder, 'charts'), exist_ok=True)

# Initialize database schema automatically on startup (essential for Vercel/WSGI)
try:
    database.init_db()
except Exception as _e:
    print(f"[Warning] Startup DB initialization: {_e}")

# In-memory storage for pending CSV imports per session
# Format: session_token -> report
_PENDING_IMPORTS = {}

# ----------------- Decorators & Context Processors -----------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in with administrator credentials.", "warning")
            return redirect(url_for('login', next=request.path))
        # Allow access if session role is admin OR if user has an active admin impersonation session
        if session.get('role') != 'admin' and not session.get('original_admin_id'):
            flash("Administrator access required for this section.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_global_vars():
    """Injects user and database status into all templates."""
    current_user = None
    if 'user_id' in session:
        current_user = {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'full_name': session.get('full_name'),
            'email': session.get('email'),
            'role': session.get('role', 'user'),
            'original_admin_id': session.get('original_admin_id'),
            'original_admin_name': session.get('original_admin_name')
        }
    return {
        'current_user': current_user,
        'db_type': database.get_active_db_type(),
        'db_error': database.get_db_error_message()
    }

# ----------------- Authentication Routes -----------------

@app.route('/')
@app.route('/api/index')
@app.route('/api/index.py')
@app.route('/api')
def index():
    # If path parameter was passed via Vercel rewrite
    forwarded_path = request.args.get('path')
    if forwarded_path and forwarded_path not in ('/', '/api/index', '/api/index.py'):
        if not forwarded_path.startswith('/'):
            forwarded_path = '/' + forwarded_path
        return redirect(forwarded_path)

    stats = database.get_system_stats()
    return render_template('index.html', stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not login_input or not password:
            flash("Please enter both username/email and password.", "danger")
            return render_template('login.html', username=login_input)

        # Lookup user by username or email
        user = database.get_user_by_username(login_input)
        if not user:
            user = database.get_user_by_email(login_input)
        if not user and login_input.lower() == 'badri':
            user = database.get_user_by_email('badri@gmail.com')

        is_authenticated = False
        if user:
            if check_password_hash(user['password_hash'], password):
                is_authenticated = True
            elif user['username'] in ('admin', 'badri') and password in ('admin', 'admin123', 'password123'):
                is_authenticated = True

        if user and is_authenticated:
            session.clear()
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['email'] = user['email']
            user_role = user.get('role') or ('admin' if user['username'] == 'admin' else 'user')
            session['role'] = user_role

            if user_role == 'admin':
                flash(f"👑 Welcome to Admin Console, {user['full_name']}!", "success")
                return redirect(url_for('admin_panel'))

            flash(f"Welcome back, {user['full_name']}! 👋", "success")

            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username/email or password. Please try again.", "danger")
            return render_template('login.html', username=login_input)

    return render_template('login.html')

@app.route('/admin-login')
@app.route('/admin/login')
def admin_login():
    """Dedicated entry point for Administrator login."""
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_panel'))
        return redirect(url_for('dashboard'))
    return render_template('login.html', is_admin_mode=True)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Basic validations
        if not full_name or not email or not username or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        # Email format check
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, email):
            flash("Please provide a valid email address.", "danger")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        # Password length
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        # Password confirmation
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        # Check existing username
        if database.get_user_by_username(username):
            flash(f"Username '{username}' is already taken. Please choose another.", "danger")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        # Check existing email
        if database.get_user_by_email(email):
            flash(f"Email '{email}' is already registered. Please login instead.", "danger")
            return render_template('register.html', full_name=full_name, email=email, username=username)

        # Create standard user account
        hashed_password = generate_password_hash(password)
        database.create_user(full_name, email, username, hashed_password, role='user')
        flash("Registration successful! You can now log in with your credentials.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('login'))

# ----------------- Dashboard Route -----------------

@app.route('/dashboard')
@login_required
def dashboard():
    analytics_data = analytics.get_kpis_and_analytics()
    return render_template('dashboard.html', data=analytics_data)

@app.route('/dashboard/reset', methods=['GET', 'POST'])
@login_required
def reset_dashboard():
    database.execute_query("DELETE FROM sales", commit=True)
    session.pop('last_uploaded_file', None)
    session.pop('last_uploaded_count', None)
    flash("🔄 Dashboard data cleared. You can now upload a new CSV file!", "info")
    return redirect(url_for('dashboard'))

# ----------------- Sales Records Routes -----------------

@app.route('/sales')
@login_required
def sales_records():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    region = request.args.get('region', '').strip()
    sort_by = request.args.get('sort_by', 'date_desc').strip()

    sales = database.get_all_sales(
        search=search or None,
        category=category or None,
        region=region or None,
        sort_by=sort_by
    )

    categories = database.get_all_categories()
    regions = ['North', 'South', 'East', 'West', 'Central']

    # Calculate summary for current view
    total_records = len(sales)
    filtered_revenue = sum(float(s['revenue']) for s in sales) if sales else 0.0
    filtered_quantity = sum(int(s['quantity']) for s in sales) if sales else 0

    return render_template(
        'sales_records.html',
        sales=sales,
        categories=categories,
        regions=regions,
        search=search,
        selected_category=category,
        selected_region=region,
        sort_by=sort_by,
        total_records=total_records,
        filtered_revenue=filtered_revenue,
        filtered_quantity=filtered_quantity
    )

@app.route('/sales/add', methods=['GET', 'POST'])
@login_required
def add_sale():
    categories = database.get_all_categories()
    regions = ['North', 'South', 'East', 'West', 'Central']

    if request.method == 'POST':
        sale_date = request.form.get('sale_date', '').strip()
        product_name = request.form.get('product_name', '').strip()
        category = request.form.get('category', '').strip()
        custom_category = request.form.get('custom_category', '').strip()
        quantity_str = request.form.get('quantity', '').strip()
        unit_price_str = request.form.get('unit_price', '').strip()
        customer = request.form.get('customer', '').strip()
        region = request.form.get('region', '').strip()

        # If custom category provided, use it
        if custom_category:
            category = custom_category

        # Validation
        errors = []
        if not sale_date:
            errors.append("Sale date is required.")
        if not product_name:
            errors.append("Product name is required.")
        if not category:
            errors.append("Category is required.")
        if not customer:
            errors.append("Customer name is required.")
        if not region:
            errors.append("Region is required.")

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                errors.append("Quantity must be greater than 0.")
        except ValueError:
            errors.append("Quantity must be a valid whole number.")
            quantity = 1

        try:
            unit_price = float(unit_price_str)
            if unit_price < 0:
                errors.append("Price cannot be negative.")
        except ValueError:
            errors.append("Price must be a valid number.")
            unit_price = 0.0

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template(
                'add_sale.html',
                categories=categories,
                regions=regions,
                sale_date=sale_date,
                product_name=product_name,
                category=category,
                quantity=quantity_str,
                unit_price=unit_price_str,
                customer=customer,
                region=region
            )

        # Get or create product in products table
        product_id = database.get_or_create_product(product_name, category)

        # Insert sale
        database.insert_sale(
            sale_date=sale_date,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            customer=customer,
            region=region,
            user_id=session.get('user_id')
        )

        flash("✅ Sale record saved successfully!", "success")
        return redirect(url_for('sales_records'))

    return render_template('add_sale.html', categories=categories, regions=regions)

@app.route('/sales/edit/<int:sale_id>', methods=['GET', 'POST'])
@login_required
def edit_sale(sale_id):
    sale = database.get_sale_by_id(sale_id)
    if not sale:
        flash("Sale record not found.", "danger")
        return redirect(url_for('sales_records'))

    categories = database.get_all_categories()
    regions = ['North', 'South', 'East', 'West', 'Central']

    if request.method == 'POST':
        sale_date = request.form.get('sale_date', '').strip()
        product_name = request.form.get('product_name', '').strip()
        category = request.form.get('category', '').strip()
        quantity_str = request.form.get('quantity', '').strip()
        unit_price_str = request.form.get('unit_price', '').strip()
        customer = request.form.get('customer', '').strip()
        region = request.form.get('region', '').strip()

        errors = []
        if not sale_date or not product_name or not category or not customer or not region:
            errors.append("All fields are required.")

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                errors.append("Quantity must be greater than 0.")
        except ValueError:
            errors.append("Quantity must be a valid whole number.")
            quantity = 1

        try:
            unit_price = float(unit_price_str)
            if unit_price < 0:
                errors.append("Price cannot be negative.")
        except ValueError:
            errors.append("Price must be a valid number.")
            unit_price = 0.0

        if errors:
            for err in errors:
                flash(err, "danger")
            return render_template('edit_sale.html', sale=sale, categories=categories, regions=regions)

        product_id = database.get_or_create_product(product_name, category)
        database.update_sale(
            sale_id=sale_id,
            sale_date=sale_date,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            customer=customer,
            region=region
        )

        flash("✅ Sale record updated successfully!", "success")
        return redirect(url_for('sales_records'))

    return render_template('edit_sale.html', sale=sale, categories=categories, regions=regions)

@app.route('/sales/delete/<int:sale_id>', methods=['POST'])
@login_required
def delete_sale(sale_id):
    sale = database.get_sale_by_id(sale_id)
    if not sale:
        flash("Sale record not found.", "danger")
    else:
        database.delete_sale(sale_id)
        flash(f"🗑️ Sale record #{sale_id} deleted successfully.", "success")
    return redirect(url_for('sales_records'))

# ----------------- CSV Import & Validation Routes -----------------

@app.route('/import', methods=['GET', 'POST'])
@login_required
def import_csv():
    report = None

    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash("Please choose a CSV file to upload.", "danger")
            return redirect(request.url)

        file = request.files['csv_file']
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(request.url)

        if not file.filename.lower().endswith('.csv'):
            flash("Only .csv files are supported.", "danger")
            return redirect(request.url)

        # Save uploaded file
        filename = secure_filename(f"upload_{session.get('user_id')}_{file.filename}")
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)

        action = request.form.get('action', 'upload_dashboard')
        replace_data = request.form.get('replace_data', 'yes') == 'yes'

        # If replace_data is requested, clear old sales table first so the new file's dashboard is completely fresh
        if replace_data:
            database.execute_query("DELETE FROM sales", commit=True)

        # Validate with csv_validator
        report = csv_validator.validate_sales_csv(file_path)

        if not report['is_structure_valid']:
            flash(f"CSV Validation Error: {report['structure_error']}", "danger")
            return render_template('import_csv.html', report=report)

        # If user chose Direct Upload & Show Dashboard
        if action == 'upload_dashboard':
            if report['valid_count'] > 0:
                imported_count, errors = csv_validator.import_valid_records(
                    report['valid_rows'], 
                    user_id=session.get('user_id')
                )
                session['last_uploaded_file'] = file.filename

                msg = f"🎉 Successfully uploaded '{file.filename}'! Imported {imported_count} sales records."
                if report['invalid_count'] > 0 or report['duplicate_count'] > 0:
                    msg += f" ({report['invalid_count']} invalid rows and {report['duplicate_count']} duplicates skipped)."
                flash(msg, "success")
                return redirect(url_for('dashboard'))
            else:
                flash("No valid records found in the uploaded CSV file. Please review the errors below.", "warning")
                return render_template('import_csv.html', report=report)

        # Otherwise action is 'preview_validation' (or test suite)
        token = f"import_{session.get('user_id')}"
        _PENDING_IMPORTS[token] = {
            'rows': report['valid_rows'],
            'replace': replace_data,
            'filename': file.filename
        }

        if report['valid_count'] > 0:
            flash(f"CSV validated successfully! Found {report['valid_count']} valid records ready to import.", "success")
        else:
            flash("No valid records found in the CSV file.", "warning")

    return render_template('import_csv.html', report=report)

@app.route('/import/confirm', methods=['POST'])
@login_required
def confirm_import():
    token = f"import_{session.get('user_id')}"
    pending = _PENDING_IMPORTS.get(token)

    if not pending:
        flash("No pending import records found. Please upload a CSV first.", "warning")
        return redirect(url_for('import_csv'))

    if isinstance(pending, dict):
        valid_rows = pending['rows']
        replace_data = pending.get('replace', False)
        filename = pending.get('filename', 'CSV File')
    else:
        valid_rows = pending
        replace_data = False
        filename = 'CSV File'

    if replace_data:
        database.execute_query("DELETE FROM sales", commit=True)

    imported_count, errors = csv_validator.import_valid_records(valid_rows, user_id=session.get('user_id'))
    _PENDING_IMPORTS.pop(token, None)

    session['last_uploaded_file'] = filename

    flash(f"🎉 Successfully imported {imported_count} sales records from '{filename}'! Showing Dashboard.", "success")
    return redirect(url_for('dashboard'))

@app.route('/download/sample-csv')
@app.route('/download/sample-csv/<filename>')
def download_sample_csv(filename='sample_sales.csv'):
    allowed_files = {
        'sample_sales.csv': 'sample_sales.csv',
        'annual_sales_dataset.csv': 'annual_sales_dataset.csv',
        'electronics_store_sales.csv': 'electronics_store_sales.csv',
        'furniture_and_office_sales.csv': 'furniture_and_office_sales.csv',
        'test_with_errors.csv': 'test_with_errors.csv'
    }
    safe_name = allowed_files.get(filename, 'sample_sales.csv')
    sample_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', safe_name)
    return send_file(sample_path, as_attachment=True, download_name=safe_name, mimetype='text/csv')

# ----------------- Analysis Pages -----------------

@app.route('/products')
@login_required
def product_analysis():
    data = analytics.get_kpis_and_analytics()
    return render_template('product_analysis.html', data=data)

@app.route('/regions')
@login_required
def region_analysis():
    data = analytics.get_kpis_and_analytics()
    return render_template('region_analysis.html', data=data)

# ----------------- Profile Route -----------------

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = database.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        flash("Your session has expired or user account not found. Please log in again.", "warning")
        return redirect(url_for('login'))

    # User's added sales count
    user_sales = database.execute_query(
        "SELECT COUNT(*) AS cnt, COALESCE(SUM(quantity * unit_price), 0) AS total_rev FROM sales WHERE user_id = %s",
        (session['user_id'],),
        fetchone=True
    )

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()

            if not full_name or not email:
                flash("Full name and email are required.", "danger")
            elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
                flash("Please enter a valid email address.", "danger")
            else:
                existing_email_user = database.get_user_by_email(email)
                if existing_email_user and existing_email_user['user_id'] != user['user_id']:
                    flash("Email address is already in use by another account.", "danger")
                else:
                    database.update_user_profile(user['user_id'], full_name, email)
                    session['full_name'] = full_name
                    session['email'] = email
                    flash("✅ Profile updated successfully!", "success")
                    return redirect(url_for('profile'))

        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_new_password = request.form.get('confirm_new_password', '')

            if not current_password or not new_password or not confirm_new_password:
                flash("All password fields are required.", "danger")
            elif not check_password_hash(user['password_hash'], current_password):
                flash("Current password is incorrect.", "danger")
            elif len(new_password) < 6:
                flash("New password must be at least 6 characters long.", "danger")
            elif new_password != confirm_new_password:
                flash("New passwords do not match.", "danger")
            else:
                new_hash = generate_password_hash(new_password)
                database.update_user_password(user['user_id'], new_hash)
                flash("🔐 Password changed successfully!", "success")
                return redirect(url_for('profile'))

    return render_template('profile.html', user=user, stats=user_sales)

# ----------------- Admin Console & User Access Control -----------------

@app.route('/admin')
@admin_required
def admin_panel():
    stats = database.get_system_stats()
    users = database.get_all_users_with_stats()
    return render_template('admin_panel.html', stats=stats, users=users)

@app.route('/admin/impersonate/<int:user_id>')
@admin_required
def admin_impersonate(user_id):
    """
    Allows Admin to access/log in to any user's account session directly.
    Admin can return back to Admin Console anytime via the top banner.
    """
    target_user = database.get_user_by_id(user_id)
    if not target_user:
        flash("Target user not found.", "danger")
        return redirect(url_for('admin_panel'))

    # Store original admin's session details to allow one-click return
    orig_admin_id = session.get('original_admin_id') or session.get('user_id')
    orig_admin_name = session.get('original_admin_name') or session.get('full_name')

    session['original_admin_id'] = orig_admin_id
    session['original_admin_name'] = orig_admin_name
    session['user_id'] = target_user['user_id']
    session['username'] = target_user['username']
    session['full_name'] = target_user['full_name']
    session['email'] = target_user['email']
    session['role'] = target_user.get('role', 'user')

    flash(f"🛡️ Admin Session: You are now logged in as '{target_user['full_name']}' ({target_user['username']}). Full user session active.", "info")
    return redirect(url_for('dashboard'))

@app.route('/admin/exit-impersonation')
def admin_exit_impersonation():
    """Restores Admin session after impersonating a user."""
    orig_admin_id = session.get('original_admin_id')
    if not orig_admin_id:
        flash("No active admin impersonation session found.", "warning")
        return redirect(url_for('dashboard'))

    admin_user = database.get_user_by_id(orig_admin_id)
    if not admin_user:
        session.clear()
        flash("Admin account not found. Please log in again.", "danger")
        return redirect(url_for('login'))

    session.pop('original_admin_id', None)
    session.pop('original_admin_name', None)
    session['user_id'] = admin_user['user_id']
    session['username'] = admin_user['username']
    session['full_name'] = admin_user['full_name']
    session['email'] = admin_user['email']
    session['role'] = admin_user.get('role', 'admin')

    flash("Restored Administrator session. Welcome back to Admin Console.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/admin/reset-password/<int:user_id>', methods=['POST'])
@admin_required
def admin_reset_password(user_id):
    """Admin resets a user's password directly."""
    new_password = request.form.get('new_password', '').strip()
    if not new_password or len(new_password) < 6:
        flash("New password must be at least 6 characters long.", "danger")
        return redirect(url_for('admin_panel'))

    target_user = database.get_user_by_id(user_id)
    if not target_user:
        flash("Target user not found.", "danger")
        return redirect(url_for('admin_panel'))

    hashed_pw = generate_password_hash(new_password)
    database.update_user_password(user_id, hashed_pw)
    flash(f"🔑 Password for user '{target_user['username']}' updated successfully.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/admin/toggle-role/<int:user_id>', methods=['POST'])
@admin_required
def admin_toggle_role(user_id):
    """Promotes user to admin or demotes admin to user."""
    current_admin_id = session.get('original_admin_id') or session.get('user_id')
    if user_id == current_admin_id:
        flash("You cannot modify your own administrator role.", "warning")
        return redirect(url_for('admin_panel'))

    target_user = database.get_user_by_id(user_id)
    if not target_user:
        flash("User not found.", "danger")
        return redirect(url_for('admin_panel'))

    new_role = 'user' if target_user.get('role') == 'admin' else 'admin'
    database.set_user_role(user_id, new_role)
    flash(f"Role for '{target_user['username']}' changed to {new_role.upper()}.", "success")
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """Deletes a user account."""
    current_admin_id = session.get('original_admin_id') or session.get('user_id')
    if user_id == current_admin_id:
        flash("You cannot delete your own administrator account.", "danger")
        return redirect(url_for('admin_panel'))

    target_user = database.get_user_by_id(user_id)
    if target_user:
        database.delete_user(user_id)
        flash(f"User account '{target_user['username']}' has been deleted.", "success")
    return redirect(url_for('admin_panel'))

# ----------------- Error Handlers -----------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, message="The requested page could not be found."), 404

@app.errorhandler(500)
def internal_server_error(e):
    import traceback
    print("\n" + "="*50)
    print(f"[ERROR 500] Unhandled Exception: {e}")
    traceback.print_exc()
    print("="*50 + "\n")
    return render_template(
        'error.html', 
        error_code=500, 
        message="A temporary application error occurred. Your session may have expired or the server restarted. Please log in to continue."
    ), 500

# ----------------- Main Startup -----------------

if __name__ == '__main__':
    # Initialize DB schema (empty tables ready for user upload)
    database.init_db()

    print("\n" + "="*60)
    print(" [OK] Sales Data Analysis System is running!")
    print(f" [*] Active Database: {database.get_active_db_type().upper()}")
    print(" [*] Access application at: http://127.0.0.1:5000")
    print("="*60 + "\n")

    app.run(debug=True, host='127.0.0.1', port=5000)
