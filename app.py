import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from google_sheets import get_credential_sheet, verify_credentials
from mikrotik import MikroTikAPI
from functools import wraps
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")
app.config['ADMIN_USERNAME'] = os.environ.get("ADMIN_USERNAME", "admin")
app.config['ADMIN_PASSWORD'] = os.environ.get("ADMIN_PASSWORD", "admin123")

# Initialize MikroTik API
mikrotik_api = MikroTikAPI(
    host=os.environ.get("MIKROTIK_HOST", "192.168.88.1"),
    username=os.environ.get("MIKROTIK_USERNAME", "admin"),
    password=os.environ.get("MIKROTIK_PASSWORD", "")
)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session or not session['admin_logged_in']:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """
    Redirect to the login page or portal landing page
    """
    # Check if it's a MikroTik captive portal request
    if request.args.get('link-login-only') and request.args.get('mac'):
        # Store MikroTik parameters in session
        session['mac'] = request.args.get('mac')
        session['ip'] = request.args.get('ip', '')
        session['username'] = request.args.get('username', '')
        session['link-login'] = request.args.get('link-login', '')
        session['link-orig'] = request.args.get('link-orig', '')
        session['error'] = request.args.get('error', '')
        
    return render_template('login.html', error=session.get('error', None))

@app.route('/login', methods=['POST'])
def login():
    """
    Process login form submission
    """
    mobile_number = request.form.get('mobile_number')
    room_number = request.form.get('room_number')
    
    # Validate input
    if not mobile_number or not room_number:
        flash('Please enter both mobile number and room number', 'danger')
        return redirect(url_for('index'))
    
    # Validate mobile number format - should start with country code (+)
    if not mobile_number.startswith('+'):
        flash('Mobile number must include country code (e.g., +911234567890)', 'danger')
        return redirect(url_for('index'))
    
    # Validate against Google Sheets
    try:
        is_valid = verify_credentials(mobile_number, room_number)
        
        if is_valid:
            # Store user info in session
            session['user_mobile'] = mobile_number
            session['user_room'] = room_number
            session['authenticated'] = True
            session['login_time'] = time.time()
            
            # Connect user to MikroTik
            try:
                # Use mobile number as username for MikroTik
                success = mikrotik_api.add_user(mobile_number, room_number)
                if success:
                    flash('Login successful!', 'success')
                    
                    # If we have MikroTik login information, redirect to their login page
                    if 'link-login' in session and session['link-login']:
                        mikrotik_login_url = f"{session['link-login']}?username={mobile_number}&password={room_number}"
                        return redirect(mikrotik_login_url)
                    
                    return render_template('login.html', success=True)
                else:
                    flash('Failed to connect to WiFi network', 'danger')
            except Exception as e:
                logger.error(f"MikroTik error: {str(e)}")
                flash('Error connecting to WiFi network', 'danger')
        else:
            flash('Invalid mobile number or room number. Please check both carefully.', 'danger')
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        flash('Error validating credentials', 'danger')
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """
    Log out the user
    """
    if 'user_mobile' in session:
        try:
            mikrotik_api.remove_user(session['user_mobile'])
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
    
    # Clear session
    session.pop('user_mobile', None)
    session.pop('user_room', None)
    session.pop('authenticated', None)
    session.pop('login_time', None)
    
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Admin login page
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['admin_logged_in'] = True
            flash('Admin login successful', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """
    Admin logout
    """
    session.pop('admin_logged_in', None)
    flash('Admin logout successful', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    """
    Admin dashboard
    """
    # Get all active users from MikroTik
    try:
        active_users = mikrotik_api.get_active_users()
    except Exception as e:
        logger.error(f"Error getting active users: {str(e)}")
        active_users = []
        flash('Error connecting to router', 'danger')
    
    return render_template('admin.html', active_users=active_users)

@app.route('/api/users')
@admin_required
def api_users():
    """
    API endpoint to get active users
    """
    try:
        active_users = mikrotik_api.get_active_users()
        return jsonify({"success": True, "users": active_users})
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/disconnect_user', methods=['POST'])
@admin_required
def api_disconnect_user():
    """
    API endpoint to disconnect a user
    """
    user_id = request.form.get('user_id')
    
    if not user_id:
        return jsonify({"success": False, "error": "No user specified"})
    
    try:
        success = mikrotik_api.remove_user(user_id)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to disconnect user"})
    except Exception as e:
        logger.error(f"Error disconnecting user: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/refresh_sheet')
@admin_required
def api_refresh_sheet():
    """
    API endpoint to refresh Google Sheet data
    """
    try:
        get_credential_sheet(force_refresh=True)
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error refreshing sheet: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error="Internal server error"), 500
