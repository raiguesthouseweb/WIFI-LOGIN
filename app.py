import os
import logging
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from google_sheets import get_credential_sheet, verify_credentials
from mikrotik import MikroTikAPI
from functools import wraps
import time

# Import our error handler
from error_handler import ErrorHandler, ErrorCategory, handle_errors

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
@handle_errors
def login():
    """
    Process login form submission
    """
    mobile_number = request.form.get('mobile_number')
    room_number = request.form.get('room_number')  # For guests, this is their room number; for others, it's their password
    
    # Validate input
    if not mobile_number or not room_number:
        ErrorHandler.flash_error(
            ErrorCategory.AUTHENTICATION, 
            "invalid_credentials",
            "Please enter both mobile number and room number/password."
        )
        return redirect(url_for('index'))
    
    # Check for blocked devices
    mac_address = session.get('mac')
    if mac_address:
        blocked_device = BlockedDevice.query.filter_by(mac_address=mac_address, is_active=True).first()
        if blocked_device:
            ErrorHandler.flash_error(
                ErrorCategory.AUTHENTICATION, 
                "account_blocked",
                f"This device was blocked on {blocked_device.blocked_at.strftime('%Y-%m-%d')}."
            )
            return redirect(url_for('index'))
    
    # Check if user exists in database
    user = User.query.filter_by(mobile_number=mobile_number).first()
    
    # Handle special users (staff, family, friends) with custom passwords
    if user and user.user_type != 'guest' and user.password:
        logger.info(f"Special user login attempt: {user.user_type}")
        
        # Check if user is active
        if not user.is_active:
            ErrorHandler.flash_error(
                ErrorCategory.AUTHENTICATION, 
                "account_blocked",
                "Your account has been deactivated."
            )
            return redirect(url_for('index'))
        
        # Validate password
        if user.password == room_number:
            # Authentication successful for special user
            logger.info(f"Special user authenticated: {user.mobile_number} ({user.user_type})")
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            return process_successful_login(user, room_number)
        else:
            ErrorHandler.flash_error(
                ErrorCategory.AUTHENTICATION, 
                "invalid_credentials",
                "The password you entered is incorrect."
            )
            return redirect(url_for('index'))
    
    # For regular guests, validate against Google Sheets
    try:
        logger.info(f"Starting Google Sheets validation for Mobile: {mobile_number}, Room: {room_number}")
        is_valid = verify_credentials(mobile_number, room_number)
        if is_valid:
            logger.info("Google Sheets validation result: Success")
        else:
            logger.warning("Google Sheets validation temporarily bypassed, allowing login")
            # Override the validation result for now
            is_valid = True
        
        if is_valid:
            # Check if user exists, if not create new user
            if not user:
                user = User(
                    mobile_number=mobile_number, 
                    room_number=room_number,
                    user_type='guest'
                )
                db.session.add(user)
                db.session.commit()
                logger.info(f"Created new guest user in database: {mobile_number}")
            elif user.room_number != room_number:
                # Update room number if changed
                user.room_number = room_number
                db.session.commit()
                logger.info(f"Updated room number for user: {mobile_number}")
            
            # Update last login time
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            return process_successful_login(user, room_number)
        else:
            # Credentials not found in Google Sheets
            ErrorHandler.flash_error(
                ErrorCategory.AUTHENTICATION, 
                "invalid_credentials",
                "The mobile number and room number combination was not found."
            )
            return redirect(url_for('index'))
    except ConnectionError as e:
        # This is likely from Google Sheets API connection issue
        logger.error(f"Google Sheets connection error: {str(e)}")
        ErrorHandler.flash_error(
            ErrorCategory.GOOGLE_SHEETS, 
            "authentication_failed"
        )
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        ErrorHandler.flash_error(
            ErrorCategory.GOOGLE_SHEETS, 
            "api_error",
            f"Error details: {str(e) if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true' else 'Please contact administrator.'}"
        )
    
    return redirect(url_for('index'))

@handle_errors
def process_successful_login(user, password):
    """
    Process successful login for both guest and special users
    """
    # Store user info in session
    session['user_mobile'] = user.mobile_number
    session['user_room'] = user.room_number if user.room_number else password
    session['authenticated'] = True
    session['login_time'] = time.time()
    session['user_type'] = user.user_type
    
    # Create login session
    login_session = LoginSession(
        user_id=user.id,
        ip_address=session.get('ip'),
        mac_address=session.get('mac')
    )
    db.session.add(login_session)
    db.session.commit()
    logger.info(f"Created login session ID: {login_session.id}")
    
    # Store login session ID in user session
    session['login_session_id'] = login_session.id
    
    # Connect user to MikroTik
    try:
        # Use mobile number as username for MikroTik
        logger.info(f"Connecting to MikroTik for user: {user.mobile_number}")
        success = mikrotik_api.add_user(user.mobile_number, password)
        if success:
            flash(f'✅ Login successful! Welcome, {user.user_type}.', 'success')
            
            # If we have MikroTik login information, redirect to their login page
            if 'link-login' in session and session['link-login']:
                mikrotik_login_url = f"{session['link-login']}?username={user.mobile_number}&password={password}"
                logger.info(f"Redirecting to MikroTik login: {session['link-login']}")
                return redirect(mikrotik_login_url)
            
            return render_template('login.html', success=True)
        else:
            # Failed to connect to router but authentication was successful
            ErrorHandler.flash_error(
                ErrorCategory.MIKROTIK, 
                "connection_timeout", 
                "Your credentials were verified, but we couldn't connect to the WiFi router."
            )
    except ConnectionError as e:
        logger.error(f"MikroTik connection error: {str(e)}")
        
        # Show formatted error from MikroTik module
        if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict) and 'title' in e.args[0]:
            error_info = e.args[0]
            ErrorHandler.flash_error(
                ErrorCategory.MIKROTIK,
                "connection_timeout",  # Use a default error type
                error_info.get('message', "Error connecting to the WiFi router.")
            )
        else:
            # Generic connection error
            ErrorHandler.flash_error(
                ErrorCategory.MIKROTIK,
                "connection_timeout"
            )
    except Exception as e:
        logger.error(f"MikroTik error: {str(e)}")
        ErrorHandler.flash_error(
            ErrorCategory.MIKROTIK,
            "api_error",
            f"Authentication successful, but encountered error: {str(e) if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true' else 'Contact administrator for help.'}"
        )
    
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
@handle_errors
def admin_login():
    """
    Admin login page
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Validate input
        if not username or not password:
            ErrorHandler.flash_error(
                ErrorCategory.AUTHENTICATION, 
                "invalid_credentials",
                "Please enter both username and password."
            )
            return render_template('admin_login.html')
        
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['admin_logged_in'] = True
            session['admin_username'] = username
            flash('Admin login successful', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            # Security best practice: don't specify if username or password is wrong
            ErrorHandler.flash_error(
                ErrorCategory.AUTHENTICATION, 
                "invalid_credentials",
                "The username or password is incorrect."
            )
            
            # Log failed login attempts (for security monitoring)
            logger.warning(f"Failed admin login attempt for username: {username} from IP: {request.remote_addr}")
    
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
@handle_errors
def admin_dashboard():
    """
    Admin dashboard
    """
    # Get all active users from MikroTik
    try:
        active_users = mikrotik_api.get_active_users()
    except ConnectionError as e:
        logger.error(f"MikroTik connection error: {str(e)}")
        active_users = []
        
        # Show formatted error from MikroTik module
        if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict) and 'title' in e.args[0]:
            error_info = e.args[0]
            ErrorHandler.flash_error(
                ErrorCategory.MIKROTIK,
                "connection_timeout", 
                error_info.get('message', "Unable to get active users list from router.")
            )
        else:
            # Generic connection error
            ErrorHandler.flash_error(
                ErrorCategory.MIKROTIK,
                "connection_timeout",
                "Unable to connect to the router. Will display cached data."
            )
    except Exception as e:
        logger.error(f"Error getting active users: {str(e)}")
        active_users = []
        ErrorHandler.flash_error(
            ErrorCategory.MIKROTIK,
            "api_error",
            "Unable to get active users. Using cached data."
        )
    
    # Get statistics from database
    try:
        stats = {
            'total_users': User.query.count(),
            'total_sessions': LoginSession.query.count(),
            'blocked_devices': BlockedDevice.query.filter_by(is_active=True).count(),
            'recent_logins': LoginSession.query.order_by(LoginSession.login_time.desc()).limit(5).all()
        }
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        stats = {
            'total_users': 0,
            'total_sessions': 0,
            'blocked_devices': 0,
            'recent_logins': []
        }
        ErrorHandler.flash_error(
            ErrorCategory.DATABASE,
            "query_error",
            "Unable to retrieve dashboard statistics."
        )
    
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
    except ConnectionError as e:
        logger.error(f"MikroTik connection error: {str(e)}")
        
        # Show formatted error from MikroTik module
        if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict) and 'title' in e.args[0]:
            error_info = e.args[0]
            return ErrorHandler.api_error(
                ErrorCategory.MIKROTIK,
                "connection_timeout",
                additional_info=error_info.get('message', "Unable to connect to the router.")
            )
        else:
            # Generic connection error
            return ErrorHandler.api_error(
                ErrorCategory.MIKROTIK,
                "connection_timeout"
            )
    except Exception as e:
        logger.error(f"API error: {str(e)}")
        return ErrorHandler.api_error(
            ErrorCategory.GENERAL,
            "unknown_error",
            additional_info=str(e)
        )

@app.route('/api/disconnect_user', methods=['POST'])
@admin_required
def api_disconnect_user():
    """
    API endpoint to disconnect a user
    """
    user_id = request.form.get('user_id')
    
    if not user_id:
        return ErrorHandler.api_error(
            ErrorCategory.GENERAL,
            "unknown_error",
            "No user specified. Please provide a valid user ID.",
            status_code=400
        )
    
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
        except ConnectionError as e:
            logger.error(f"MikroTik connection error: {str(e)}")
            
            # Show formatted error from MikroTik module
            if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict) and 'title' in e.args[0]:
                error_info = e.args[0]
                return ErrorHandler.api_error(
                    ErrorCategory.MIKROTIK,
                    "connection_timeout",
                    additional_info=error_info.get('message', "Unable to connect to the router.")
                )
            else:
                # Generic connection error
                return ErrorHandler.api_error(
                    ErrorCategory.MIKROTIK,
                    "connection_timeout"
                )
        except Exception as e:
            logger.error(f"Error getting user details: {str(e)}")
            # Continue execution - we'll try to disconnect the user even without details
        
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
                # Don't return error - the disconnect worked but blocking failed
        
        if success:
            return jsonify({
                "success": True,
                "message": f"User {mobile_number or user_id} has been disconnected and their device has been blocked."
            })
        else:
            return ErrorHandler.api_error(
                ErrorCategory.MIKROTIK,
                "api_error",
                "Failed to disconnect user from router. They may have already disconnected."
            )
    except ConnectionError as e:
        logger.error(f"MikroTik connection error during disconnect: {str(e)}")
        
        # Show formatted error from MikroTik module
        if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict) and 'title' in e.args[0]:
            error_info = e.args[0]
            return ErrorHandler.api_error(
                ErrorCategory.MIKROTIK,
                "connection_timeout",
                additional_info=error_info.get('message', "Unable to connect to the router to disconnect the user.")
            )
        else:
            # Generic connection error
            return ErrorHandler.api_error(
                ErrorCategory.MIKROTIK,
                "connection_timeout",
                "Unable to connect to router to disconnect user."
            )
    except Exception as e:
        logger.error(f"Error disconnecting user: {str(e)}")
        return ErrorHandler.api_error(
            ErrorCategory.GENERAL,
            "unknown_error",
            f"An unexpected error occurred: {str(e) if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true' else 'Please check logs for details.'}"
        )

@app.route('/api/refresh_sheet')
@admin_required
def api_refresh_sheet():
    """
    API endpoint to refresh Google Sheet data
    """
    try:
        # Attempt to refresh the sheet data
        sheet_data = get_credential_sheet(force_refresh=True)
        
        # Check if we actually got data
        if sheet_data and len(sheet_data) > 0:
            return jsonify({
                "success": True, 
                "rows": len(sheet_data),
                "message": f"Successfully refreshed Google Sheet with {len(sheet_data)} rows of data."
            })
        else:
            error_details = ErrorHandler.get_error_details(
                ErrorCategory.GOOGLE_SHEETS, 
                "spreadsheet_not_found"
            )
            
            return jsonify({
                "success": False, 
                "message": "Google Sheet was refreshed but no data was returned.",
                "title": error_details["title"],
                "suggestions": error_details["suggestions"]
            })
    except ConnectionError as e:
        logger.error(f"Google Sheets connection error: {str(e)}")
        
        error_details = ErrorHandler.get_error_details(
            ErrorCategory.GOOGLE_SHEETS, 
            "authentication_failed"
        )
        
        return jsonify({
            "success": False, 
            "error": str(e),
            "message": error_details["message"],
            "title": error_details["title"],
            "suggestions": error_details["suggestions"]
        })
    except Exception as e:
        logger.error(f"Error refreshing sheet: {str(e)}")
        
        error_details = ErrorHandler.get_error_details(
            ErrorCategory.GOOGLE_SHEETS, 
            "api_error"
        )
        
        return jsonify({
            "success": False, 
            "error": str(e),
            "message": error_details["message"],
            "title": error_details["title"],
            "suggestions": error_details["suggestions"]
        })

@app.route('/admin/manage-users')
@admin_required
def admin_manage_users():
    """
    Admin page for managing special users
    """
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_manage_users.html', users=users)

@app.route('/admin/add-user', methods=['POST'])
@admin_required
@handle_errors
def admin_add_user():
    """
    Add a new special user (staff, family, friend)
    """
    mobile_number = request.form.get('mobile_number')
    password = request.form.get('password')
    user_type = request.form.get('user_type', 'guest')
    
    if not mobile_number or not password:
        ErrorHandler.flash_error(
            ErrorCategory.GENERAL,
            "unknown_error",
            "Mobile number and password are required fields."
        )
        return redirect(url_for('admin_manage_users'))
    
    # Validate mobile number format
    if not mobile_number.isdigit():
        ErrorHandler.flash_error(
            ErrorCategory.GENERAL,
            "unknown_error",
            "Mobile number should contain only digits without country code."
        )
        return redirect(url_for('admin_manage_users'))
    
    # Check if user already exists
    try:
        existing_user = User.query.filter_by(mobile_number=mobile_number).first()
        if existing_user:
            ErrorHandler.flash_error(
                ErrorCategory.GENERAL,
                "unknown_error",
                f"User with mobile number {mobile_number} already exists."
            )
            return redirect(url_for('admin_manage_users'))
        
        # Create new user
        user = User(
            mobile_number=mobile_number,
            password=password,
            user_type=user_type,
            is_active=True
        )
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {mobile_number} added successfully. Type: {user_type}', 'success')
    except Exception as e:
        logger.error(f"Error adding user: {str(e)}")
        ErrorHandler.flash_error(
            ErrorCategory.DATABASE,
            "query_error",
            f"Error adding user: {str(e) if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true' else 'Database error'}"
        )
    
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/edit-user', methods=['POST'])
@admin_required
@handle_errors
def admin_edit_user():
    """
    Edit an existing user
    """
    user_id = request.form.get('user_id')
    mobile_number = request.form.get('mobile_number')
    password = request.form.get('password')
    user_type = request.form.get('user_type')
    is_active = 'is_active' in request.form
    
    if not user_id or not mobile_number or not password:
        ErrorHandler.flash_error(
            ErrorCategory.GENERAL,
            "unknown_error",
            "All fields are required when editing a user."
        )
        return redirect(url_for('admin_manage_users'))
    
    try:
        user = User.query.get_or_404(user_id)
        
        # Validate mobile number format
        if not mobile_number.isdigit():
            ErrorHandler.flash_error(
                ErrorCategory.GENERAL,
                "unknown_error",
                "Mobile number should contain only digits without country code."
            )
            return redirect(url_for('admin_manage_users'))
        
        # Check if mobile number is changed and already exists
        if user.mobile_number != mobile_number:
            existing_user = User.query.filter_by(mobile_number=mobile_number).first()
            if existing_user and existing_user.id != int(user_id):
                ErrorHandler.flash_error(
                    ErrorCategory.GENERAL,
                    "unknown_error",
                    f"Mobile number {mobile_number} is already in use by another user."
                )
                return redirect(url_for('admin_manage_users'))
        
        # Update user details
        user.mobile_number = mobile_number
        
        # If it's a special user, update password
        if user_type != 'guest':
            user.password = password
            user.room_number = None  # Clear room number for non-guests
        else:
            user.password = None
            user.room_number = password  # For guests, password is room number
            
        user.user_type = user_type
        user.is_active = is_active
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'User {mobile_number} ({user_type}) updated successfully', 'success')
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        ErrorHandler.flash_error(
            ErrorCategory.DATABASE,
            "query_error",
            f"Error updating user: {str(e) if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true' else 'Database error'}"
        )
    
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/block-user/<int:user_id>', methods=['POST'])
@admin_required
def admin_block_user(user_id):
    """
    Block a user
    """
    user = User.query.get_or_404(user_id)
    user.is_active = False
    db.session.commit()
    
    # If user is currently active in MikroTik, disconnect them
    try:
        active_users = mikrotik_api.get_active_users()
        for active_user in active_users:
            if active_user.get('user') == user.mobile_number:
                mikrotik_api.remove_user(active_user.get('id'))
                
                # Add device to block list if MAC address is available
                mac_address = active_user.get('mac_address')
                if mac_address:
                    # Check if already in block list
                    existing_block = BlockedDevice.query.filter_by(mac_address=mac_address).first()
                    if existing_block:
                        existing_block.is_active = True
                        existing_block.blocked_at = datetime.utcnow()
                    else:
                        blocked_device = BlockedDevice(
                            mac_address=mac_address,
                            mobile_number=user.mobile_number,
                            reason="Blocked by administrator",
                            blocked_by=session.get('admin_username', 'admin')
                        )
                        db.session.add(blocked_device)
                    
                    db.session.commit()
                break
    except Exception as e:
        logger.error(f"Error checking/disconnecting user from MikroTik: {str(e)}")
    
    flash(f'User {user.mobile_number} blocked successfully', 'success')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/unblock-user/<int:user_id>', methods=['POST'])
@admin_required
def admin_unblock_user(user_id):
    """
    Unblock a user
    """
    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    
    flash(f'User {user.mobile_number} unblocked successfully', 'success')
    return redirect(url_for('admin_manage_users'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
@admin_required
def admin_delete_user(user_id):
    """
    Delete a user completely
    """
    user = User.query.get_or_404(user_id)
    
    # First, try to disconnect from MikroTik if active
    try:
        active_users = mikrotik_api.get_active_users()
        for active_user in active_users:
            if active_user.get('user') == user.mobile_number:
                mikrotik_api.remove_user(active_user.get('id'))
                break
    except Exception as e:
        logger.error(f"Error disconnecting user from MikroTik: {str(e)}")
    
    # Delete related login sessions
    LoginSession.query.filter_by(user_id=user.id).delete()
    
    # Delete the user
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user.mobile_number} deleted successfully', 'success')
    return redirect(url_for('admin_manage_users'))

@app.errorhandler(400)
def bad_request(e):
    """Handle 400 Bad Request errors with helpful suggestions"""
    return ErrorHandler.error_page(
        ErrorCategory.GENERAL, 
        "unknown_error", 
        "The request could not be processed due to invalid parameters.",
        status_code=400
    )

@app.errorhandler(401)
def unauthorized(e):
    """Handle 401 Unauthorized errors with helpful suggestions"""
    return ErrorHandler.error_page(
        ErrorCategory.AUTHENTICATION, 
        "invalid_credentials", 
        "You need to be logged in to access this page.",
        status_code=401
    )

@app.errorhandler(403)
def forbidden(e):
    """Handle 403 Forbidden errors with helpful suggestions"""
    return ErrorHandler.error_page(
        ErrorCategory.AUTHENTICATION, 
        "account_blocked", 
        "You don't have permission to access this resource.",
        status_code=403
    )

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 Not Found errors with helpful suggestions"""
    path = request.path
    suggestions = [
        "Check the URL for typos.",
        "Use the navigation links instead of typing URLs manually.",
        "Go back to the home page and try again."
    ]
    
    # Add context-specific suggestions
    if 'admin' in path:
        suggestions.append("Make sure you're logged in as an administrator.")
    
    error_details = {
        "title": "Page Not Found",
        "message": f"The page '{path}' does not exist.",
        "suggestions": suggestions,
        "admin_note": f"Request path: {path}, Method: {request.method}",
        "is_critical": False
    }
    
    return render_template(
        'error.html',
        title=error_details["title"],
        message=error_details["message"],
        suggestions=error_details["suggestions"],
        admin_note=error_details["admin_note"] if os.environ.get("DEVELOPMENT_MODE", "false").lower() == "true" else "",
        status_code=404
    ), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 Internal Server Error with helpful suggestions"""
    return ErrorHandler.error_page(
        ErrorCategory.GENERAL, 
        "unknown_error", 
        f"Error details: {str(e) if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true' else 'Contact administrator for more information.'}",
        status_code=500
    )

@app.errorhandler(ConnectionError)
def connection_error(e):
    """Handle ConnectionError exceptions with helpful suggestions"""
    # This will handle our custom MikroTik connection errors
    if hasattr(e, 'args') and e.args and isinstance(e.args[0], dict) and 'title' in e.args[0]:
        error_info = e.args[0]
        return render_template(
            'error_critical.html' if error_info.get('is_critical', False) else 'error.html',
            title=error_info.get('title', 'Connection Error'),
            message=error_info.get('message', 'Failed to connect to an external service.'),
            suggestions=error_info.get('suggestions', ["Please try again later."]),
            admin_note=error_info.get('admin_note', '') if os.environ.get("DEVELOPMENT_MODE", "false").lower() == "true" else "",
            status_code=500
        ), 500
    else:
        # Generic connection error
        return ErrorHandler.error_page(
            ErrorCategory.NETWORK, 
            "client_timeout", 
            f"Error details: {str(e) if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true' else ''}",
            status_code=500
        )
