"""
Comprehensive Automated Test Suite for Sales Data Analysis System
"""

import os
import unittest
import io
import time
from app import app
import database

class SalesAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        cls.client = app.test_client()
        database.init_db()

        # Clean existing test users if any
        database.execute_query("DELETE FROM users WHERE username LIKE 'test_%' OR username LIKE '%user%'", commit=True)
        database.execute_query("DELETE FROM sales", commit=True)

    @classmethod
    def tearDownClass(cls):
        # Always clean up test sales and test users so active DB remains pristine
        database.execute_query("DELETE FROM sales", commit=True)
        database.execute_query("DELETE FROM users WHERE username LIKE 'test_%' OR username LIKE '%user%'", commit=True)

    def test_01_redirect_unauthenticated_user(self):
        """Unauthenticated user accessing protected routes should be redirected to login."""
        protected_routes = ['/dashboard', '/sales', '/sales/add', '/import', '/products', '/regions', '/profile']
        for route in protected_routes:
            resp = self.client.get(route, follow_redirects=False)
            self.assertEqual(resp.status_code, 302, f"Expected redirect on {route}")
            self.assertIn('/login', resp.headers['Location'])

    def test_02_register_user(self):
        """User registration and duplicate checking."""
        uid = int(time.time() * 1000) % 1000000
        username = f"tester_{uid}"
        email = f"tester_{uid}@example.com"

        resp = self.client.post('/register', data={
            'full_name': 'Test Engineer',
            'email': email,
            'username': username,
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Registration successful", resp.data)

        # Duplicate username attempt
        resp_dup = self.client.post('/register', data={
            'full_name': 'Another Tester',
            'email': f"another_{uid}@example.com",
            'username': username,
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertIn(b"already taken", resp_dup.data)

    def test_03_login_and_logout(self):
        """User login and logout."""
        from werkzeug.security import generate_password_hash
        database.create_user('Login User', 'login@example.com', 'tloginuser', generate_password_hash('pass123'))

        client = app.test_client()

        # Bad login
        bad_resp = client.post('/login', data={
            'username': 'tloginuser',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertIn(b"Invalid username/email or password", bad_resp.data)

        # Good login
        good_resp = client.post('/login', data={
            'username': 'tloginuser',
            'password': 'pass123'
        }, follow_redirects=True)
        self.assertEqual(good_resp.status_code, 200)
        self.assertIn(b"Sales Data Analysis Dashboard", good_resp.data)

        # Logout
        logout_resp = client.get('/logout', follow_redirects=True)
        self.assertIn(b"logged out successfully", logout_resp.data)

    def test_04_full_sales_lifecycle(self):
        """Tests complete user journey: Login -> Add Sale -> Search -> Edit -> Delete."""
        from werkzeug.security import generate_password_hash
        user = database.get_user_by_username('tjourney_user')
        if not user:
            database.create_user('Journey User', 'journey@example.com', 'tjourney_user', generate_password_hash('pass123'))
        
        client = app.test_client()
        client.post('/login', data={'username': 'tjourney_user', 'password': 'pass123'}, follow_redirects=True)

        # 1. Dashboard
        resp_dash = client.get('/dashboard')
        self.assertEqual(resp_dash.status_code, 200)
        self.assertIn(b"Sales Data Analysis Dashboard", resp_dash.data)

        # 2. Add Sale
        resp_add = client.post('/sales/add', data={
            'sale_date': '2026-11-01',
            'product_name': 'Mechanical Keyboard V2',
            'category': 'Electronics',
            'quantity': '5',
            'unit_price': '120.00',
            'customer': 'Bruce Wayne',
            'region': 'West'
        }, follow_redirects=True)
        self.assertEqual(resp_add.status_code, 200)
        self.assertIn(b"Sale record saved successfully", resp_add.data)
        self.assertIn(b"Bruce Wayne", resp_add.data)

        # 3. Search and filter
        resp_search = client.get('/sales?search=Bruce+Wayne')
        self.assertIn(b"Bruce Wayne", resp_search.data)
        self.assertIn(b"$600.00", resp_search.data)  # 5 * 120 = 600

        # 4. Edit Sale
        sales = database.get_all_sales(search='Bruce Wayne')
        self.assertTrue(len(sales) > 0)
        sale_id = sales[0]['sale_id']

        resp_edit = client.post(f'/sales/edit/{sale_id}', data={
            'sale_date': '2026-11-01',
            'product_name': 'Mechanical Keyboard V2',
            'category': 'Electronics',
            'quantity': '10',
            'unit_price': '120.00',
            'customer': 'Bruce Wayne',
            'region': 'West'
        }, follow_redirects=True)
        self.assertEqual(resp_edit.status_code, 200)
        self.assertIn(b"Sale record updated successfully", resp_edit.data)
        self.assertIn(b"$1,200.00", resp_edit.data)  # 10 * 120 = 1200

        # 5. Delete Sale
        resp_del = client.post(f'/sales/delete/{sale_id}', follow_redirects=True)
        self.assertEqual(resp_del.status_code, 200)
        self.assertIn(b"deleted successfully", resp_del.data)

    def test_05_csv_import_workflow(self):
        """Tests uploading CSV, validation report rendering, and confirmation import."""
        from werkzeug.security import generate_password_hash
        user = database.get_user_by_username('tcsv_user')
        if not user:
            database.create_user('CSV User', 'csv@example.com', 'tcsv_user', generate_password_hash('pass123'))

        client = app.test_client()
        client.post('/login', data={'username': 'tcsv_user', 'password': 'pass123'}, follow_redirects=True)

        # Upload erroneous test CSV
        test_csv_path = os.path.join(os.path.dirname(__file__), 'data', 'test_with_errors.csv')
        with open(test_csv_path, 'rb') as f:
            csv_bytes = f.read()

        # 1. Preview Validation Mode
        data_preview = {
            'csv_file': (io.BytesIO(csv_bytes), 'test_with_errors.csv'),
            'action': 'preview_validation'
        }
        resp = client.post('/import', data=data_preview, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"VALID RECORDS", resp.data)
        self.assertIn(b"INVALID RECORDS", resp.data)
        self.assertIn(b"DUPLICATE RECORDS", resp.data)
        self.assertIn(b"Error Reason", resp.data)

        # 2. Confirm import of valid rows -> Goes to Dashboard
        confirm_resp = client.post('/import/confirm', follow_redirects=True)
        self.assertEqual(confirm_resp.status_code, 200)
        self.assertIn(b"Sales Data Analysis Dashboard", confirm_resp.data)

        # 3. Direct Upload to Dashboard Mode
        data_direct = {
            'csv_file': (io.BytesIO(csv_bytes), 'test_with_errors.csv'),
            'action': 'upload_dashboard',
            'replace_data': 'yes'
        }
        direct_resp = client.post('/import', data=data_direct, content_type='multipart/form-data', follow_redirects=True)
        self.assertEqual(direct_resp.status_code, 200)
        self.assertIn(b"Sales Data Analysis Dashboard", direct_resp.data)

    def test_06_analysis_and_profile_routes(self):
        """Tests products analysis, region analysis, and profile update."""
        from werkzeug.security import generate_password_hash
        user = database.get_user_by_username('tprof_user')
        if not user:
            database.create_user('Profile User', 'prof@example.com', 'tprof_user', generate_password_hash('pass123'))

        client = app.test_client()
        client.post('/login', data={'username': 'tprof_user', 'password': 'pass123'}, follow_redirects=True)

        # Products
        r_prod = client.get('/products')
        self.assertEqual(r_prod.status_code, 200)
        self.assertIn(b"Product-wise Sales", r_prod.data)

        # Regions
        r_reg = client.get('/regions')
        self.assertEqual(r_reg.status_code, 200)
        self.assertIn(b"Region-wise Sales", r_reg.data)

        # Profile GET
        r_prof = client.get('/profile')
        self.assertEqual(r_prof.status_code, 200)
        self.assertIn(b"My Profile", r_prof.data)

        # Profile Update POST
        r_update = client.post('/profile', data={
            'action': 'update_profile',
            'full_name': 'Profile User Renamed',
            'email': 'prof_renamed@example.com'
        }, follow_redirects=True)
        self.assertEqual(r_update.status_code, 200)
        self.assertIn(b"Profile updated successfully", r_update.data)

    def test_07_download_sample_csv(self):
        """Tests downloading the sample CSV file."""
        resp = self.client.get('/download/sample-csv')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/csv', resp.content_type)
        self.assertIn(b"sale_id,product_id,product_name", resp.data)

    def test_08_front_page_and_admin_impersonation(self):
        """Tests front page features and admin access over user login."""
        # 1. Front page shows website features
        resp_front = self.client.get('/')
        self.assertEqual(resp_front.status_code, 200)
        self.assertIn(b"Features of the Website", resp_front.data)

        # 2. Admin login
        client = app.test_client()
        resp_login = client.post('/login', data={'username': 'admin', 'password': 'admin123'}, follow_redirects=False)
        self.assertEqual(resp_login.status_code, 302)
        self.assertIn('/admin', resp_login.headers.get('Location', ''))

        # 3. Admin panel
        resp_panel = client.get('/admin')
        self.assertEqual(resp_panel.status_code, 200)
        self.assertIn(b"Admin Control Center", resp_panel.data)
        self.assertIn(b"Access Account", resp_panel.data)

        # 4. Impersonate user
        users = database.get_all_users_with_stats()
        target_user = [u for u in users if u['role'] != 'admin'][0]
        resp_imp = client.get(f"/admin/impersonate/{target_user['user_id']}", follow_redirects=True)
        self.assertEqual(resp_imp.status_code, 200)
        self.assertIn(b"Admin Mode Active", resp_imp.data)

        # 5. Exit impersonation back to admin
        resp_exit = client.get('/admin/exit-impersonation', follow_redirects=True)
        self.assertEqual(resp_exit.status_code, 200)
        self.assertIn(b"Admin Control Center", resp_exit.data)

if __name__ == '__main__':
    unittest.main()
