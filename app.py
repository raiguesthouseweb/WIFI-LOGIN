import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from google_sheets import get_credential_sheet, verify_credentials
from mikrotik import MikroTikAPI
from functools import wraps
import time

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get the Flask app instance and db from main.py
from main import app, db

app.config['ADMIN_USERNAME'] = os.environ.get("ADMIN_USERNAME", "admin")
app.config['ADMIN_PASSWORD'] = os.environ.get("ADMIN_PASSWORD", "admin123")

# Initialize MikroTik API
mikrotik_api = MikroTikAPI(
    host=os.environ.get("MIKROTIK_HOST", "192.168.88.1"),
    username=os.environ.get("MIKROTIK_USERNAME", "admin"),
    password=os.environ.get("MIKROTIK_PASSWORD", "")
)

# Import models
from models import User, LoginSession, BlockedDevice, GoogleCredential

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
    
    # No country code validation needed
    # Mobile number validation is handled by Google Sheets
    
    # Check for blocked devices
    mac_address = session.get('mac')
    if mac_address:
        blocked_device = BlockedDevice.query.filter_by(mac_address=mac_address, is_active=True).first()
        if blocked_device:
            flash('This device has been blocked by the administrator', 'danger')
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
            
            # Check if user exists in database, if not create new user
            user = User.query.filter_by(mobile_number=mobile_number).first()
            if not user:
                user = User(mobile_number=mobile_number, room_number=room_number)
                db.session.add(user)
                db.session.commit()
            elif user.room_number != room_number:
                # Update room number if changed
                user.room_number = room_number
                db.session.commit()
            
            # Create login session
            login_session = LoginSession(
                user_id=user.id,
                ip_address=session.get('ip'),
                mac_address=session.get('mac')
            )
            db.session.add(login_session)
            db.session.commit()
            
            # Store login session ID in user session
            session['login_session_id'] = login_session.id
            
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
    
    # Update login session record if it exists
    if 'login_session_id' in session:
        try:
            login_session = LoginSession.query.get(session['login_session_id'])
            if login_session:
                login_session.logout_time = datetime.utcnow()
                
                # Try to update bytes in/out from MikroTik if available
                try:
                    # This would need to be implemented based on your specific MikroTik API
                    pass
                except Exception as e:
                    logger.error(f"Error updating session data: {str(e)}")
                
                db.session.commit()
        except Exception as e:
            logger.error(f"Error updating login session: {str(e)}")
    
    # Clear session
    session.pop('user_mobile', None)
    session.pop('user_room', None)
    session.pop('authenticated', None)
    session.pop('login_time', None)
    session.pop('login_session_id', None)
    
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
    
    # Get statistics from database
    stats = {
        'total_users': User.query.count(),
        'total_sessions': LoginSession.query.count(),
        'blocked_devices': BlockedDevice.query.filter_by(is_active=True).count(),
        'recent_logins': LoginSession.query.order_by(LoginSession.login_time.desc()).limit(5).all()
    }
    
    return render_template('admin.html', active_users=active_users, stats=stats)

@app.route('/admin/users')
@admin_required
def admin_users():
    """
    Admin users page - shows all registered users
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/sessions')
@admin_required
def admin_sessions():
    """
    Admin sessions page - shows login history
    """
    sessions = LoginSession.query.order_by(LoginSession.login_time.desc()).all()
    return render_template('admin_sessions.html', sessions=sessions)

@app.route('/admin/blocked')
@admin_required
def admin_blocked():
    """
    Admin blocked devices page
    """
    blocked_devices = BlockedDevice.query.order_by(BlockedDevice.blocked_at.desc()).all()
    return render_template('admin_blocked.html', blocked_devices=blocked_devices)

@app.route('/admin/unblock/<int:device_id>', methods=['POST'])
@admin_required
def admin_unblock(device_id):
    """
    Unblock a device
    """
    device = BlockedDevice.query.get_or_404(device_id)
    device.is_active = False
    db.session.commit()
    flash(f'Device {device.mac_address} unblocked successfully', 'success')
    return redirect(url_for('admin_blocked'))

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
        # Get user details before disconnection to add to block list
        user_details = None
        mac_address = None
        mobile_number = None
        
        try:
            # Get active users from MikroTik
            active_users = mikrotik_api.get_active_users()
            for user in active_users:
                if user.get('id') == user_id:
                    user_details = user
                    mac_address = user.get('mac_address')
                    mobile_number = user.get('user')
                    break
        except Exception as e:
            logger.error(f"Error getting user details: {str(e)}")
        
        # Disconnect the user
        success = mikrotik_api.remove_user(user_id)
        
        if success and mac_address:
            # Add to database block list
            try:
                # Check if already in block list
                existing_block = BlockedDevice.query.filter_by(mac_address=mac_address).first()
                
                if existing_block:
                    # Update existing block
                    existing_block.is_active = True
                    existing_block.blocked_at = datetime.utcnow()
                    existing_block.blocked_by = session.get('admin_username', 'admin')
                    existing_block.reason = "Disconnected by administrator"
                else:
                    # Create new block
                    blocked_device = BlockedDevice(
                        mac_address=mac_address,
                        mobile_number=mobile_number,
                        reason="Disconnected by administrator",
                        blocked_by=session.get('admin_username', 'admin')
                    )
                    db.session.add(blocked_device)
                
                db.session.commit()
                logger.info(f"Added MAC {mac_address} to database block list")
            except Exception as e:
                logger.error(f"Error adding to database block list: {str(e)}")
        
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
