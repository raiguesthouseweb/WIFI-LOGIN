# MikroTik Captive Portal System
## Complete Technical Documentation

<style>
body {
    font-family: 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 1000px;
    margin: 0 auto;
    padding: 20px;
}

h1 {
    color: #2a5885;
    border-bottom: 2px solid #2a5885;
    padding-bottom: 10px;
}

h2 {
    color: #3b7ea1;
    border-left: 4px solid #3b7ea1;
    padding-left: 10px;
    margin-top: 30px;
}

h3 {
    color: #4b94b3;
    margin-top: 25px;
}

h4 {
    color: #5ba9c6;
}

.highlight {
    background-color: #f8f9fa;
    border-left: 4px solid #5ba9c6;
    padding: 15px;
    margin: 20px 0;
    overflow-x: auto;
}

code {
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
    background-color: #f5f5f5;
    padding: 2px 4px;
    border-radius: 3px;
    font-size: 0.9em;
}

pre {
    background-color: #f5f5f5;
    padding: 15px;
    border-radius: 5px;
    overflow-x: auto;
}

pre code {
    background-color: transparent;
    padding: 0;
}

blockquote {
    border-left: 4px solid #ddd;
    padding-left: 15px;
    color: #666;
    margin: 20px 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 20px 0;
}

table, th, td {
    border: 1px solid #ddd;
}

th, td {
    padding: 12px;
    text-align: left;
}

th {
    background-color: #f2f2f2;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

.section {
    margin-bottom: 30px;
}

.note {
    background-color: #e6f6ff;
    border-left: 4px solid #1890ff;
    padding: 15px;
    margin: 20px 0;
}

.warning {
    background-color: #fff7e6;
    border-left: 4px solid #fa8c16;
    padding: 15px;
    margin: 20px 0;
}

.success {
    background-color: #f6ffed;
    border-left: 4px solid #52c41a;
    padding: 15px;
    margin: 20px 0;
}

.feature-box {
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
}

.feature-title {
    background-color: #f2f2f2;
    padding: 10px;
    margin: -20px -20px 20px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    font-weight: bold;
    color: #333;
}

.screenshot {
    max-width: 100%;
    border: 1px solid #ddd;
    border-radius: 5px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin: 20px 0;
}

.code-filename {
    background-color: #e8e8e8;
    color: #333;
    padding: 5px 10px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    margin-bottom: -20px;
    font-size: 0.8em;
    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.flow-chart {
    width: 100%;
    margin: 20px 0;
    padding: 15px;
    border: 1px solid #ddd;
    border-radius: 5px;
}
</style>

<div style="text-align: center; margin-bottom: 40px;">
    <h1 style="font-size: 2.5em; margin-bottom: 10px; color: #2a5885;">MikroTik Captive Portal System</h1>
    <p style="font-size: 1.2em; color: #666;">Technical Documentation & Implementation Guide</p>
    <hr style="width: 50%; margin: 20px auto;">
    <p>Version 1.0 | April 2025</p>
</div>

## Table of Contents

1. [Core Architecture](#1-core-architecture-files)
2. [External Integrations](#2-external-integration-files)
3. [Authentication Flows](#3-user-authentication-flow)
4. [Admin Panel Features](#4-admin-panel-features)
5. [Technical Implementation](#5-technical-implementation-details)
6. [Deployment Guide](#6-deployment-preparation)
7. [Additional Documentation](#7-additional-documentation)

---

## 1. Core Architecture Files

The application is built on a Flask backend with SQLAlchemy for database interaction and follows an MVC-like structure.

<div class="feature-box">
    <div class="feature-title">main.py</div>
    <p><strong>Purpose:</strong> Application entry point and configuration.</p>
    
    <h4>Key Components:</h4>
    <ul>
        <li>Database connection setup via SQLAlchemy</li>
        <li>Flask application initialization</li>
        <li>Environment variables configuration</li>
        <li>Server startup parameters (host="0.0.0.0", port=5000)</li>
    </ul>
    
    <div class="highlight">
    <div class="code-filename">main.py</div>
    <pre><code># Database initialization
db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")
database_url = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Create tables
with app.app_context():
    import models
    db.create_all()</code></pre>
    </div>
</div>

<div class="feature-box">
    <div class="feature-title">models.py</div>
    <p><strong>Purpose:</strong> Defines database models using SQLAlchemy ORM.</p>
    
    <h4>Key Models:</h4>
    <ol>
        <li><strong>User:</strong> Stores user information and credentials
            <ul>
                <li>Regular guests (Google Sheet validation)</li>
                <li>Special users (staff, family, friends with custom credentials)</li>
            </ul>
        </li>
        <li><strong>LoginSession:</strong> Tracks user login/logout activity</li>
        <li><strong>BlockedDevice:</strong> Manages blocked MAC addresses</li>
        <li><strong>GoogleCredential:</strong> Stores Google API credentials</li>
    </ol>
    
    <h4>Model Relationships:</h4>
    <ul>
        <li>One-to-many relationship between <code>User</code> and <code>LoginSession</code></li>
    </ul>
    
    <div class="highlight">
    <div class="code-filename">models.py</div>
    <pre><code>class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    mobile_number = db.Column(db.String(20), unique=True, nullable=False)
    room_number = db.Column(db.String(20), nullable=True)  # For guests
    password = db.Column(db.String(100), nullable=True)    # For special users
    user_type = db.Column(db.String(20), default='guest')  # guest, staff, family, friend
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    login_sessions = db.relationship('LoginSession', backref='user', lazy=True)</code></pre>
    </div>
</div>

<div class="feature-box">
    <div class="feature-title">app.py</div>
    <p><strong>Purpose:</strong> Contains all route handlers and application logic.</p>
    
    <h4>Key Routes:</h4>
    <ul>
        <li><strong>User Authentication:</strong>
            <ul>
                <li><code>/</code>: Main index/login page</li>
                <li><code>/login</code>: Processes login form</li>
                <li><code>/logout</code>: Handles user logout</li>
            </ul>
        </li>
        <li><strong>Admin Panel:</strong>
            <ul>
                <li><code>/admin/login</code>: Admin authentication</li>
                <li><code>/admin</code>: Dashboard with network stats</li>
                <li><code>/admin/users</code>: Registered users list</li>
                <li><code>/admin/sessions</code>: Login history</li>
                <li><code>/admin/blocked</code>: Blocked device management</li>
                <li><code>/admin/manage-users</code>: Special user management</li>
            </ul>
        </li>
        <li><strong>API Endpoints:</strong>
            <ul>
                <li><code>/api/users</code>: Get active users (AJAX)</li>
                <li><code>/api/disconnect_user</code>: Remove user from network</li>
                <li><code>/api/refresh_sheet</code>: Update Google Sheet data</li>
            </ul>
        </li>
    </ul>
    
    <h4>Authentication Logic:</h4>
    <ul>
        <li>Guest authentication (via Google Sheets)</li>
        <li>Special user authentication (via database)</li>
        <li>Admin authentication (via environment variables)</li>
    </ul>
    
    <h4>Key Features:</h4>
    <ul>
        <li>User session management with Flask sessions</li>
        <li>Automatic user creation for first-time logins</li>
        <li>MAC address tracking and blocking</li>
    </ul>
</div>

## 2. External Integration Files

<div class="feature-box">
    <div class="feature-title">mikrotik.py</div>
    <p><strong>Purpose:</strong> Handles communication with MikroTik router via API.</p>
    
    <h4>Key Functions:</h4>
    <ul>
        <li><code>connect()</code>: Establishes connection to router</li>
        <li><code>get_active_users()</code>: Retrieves connected clients</li>
        <li><code>add_user()</code>: Authenticates users to the hotspot</li>
        <li><code>remove_user()</code>: Disconnects users</li>
        <li><code>_block_mac_address()</code>: Blocks MAC addresses</li>
    </ul>
    
    <h4>Error Handling:</h4>
    <ul>
        <li>Connection timeouts</li>
        <li>Authentication failures</li>
        <li>Development mode for offline testing</li>
    </ul>
    
    <div class="highlight">
    <div class="code-filename">mikrotik.py (usage example)</div>
    <pre><code># Initialize MikroTik API
mikrotik_api = MikroTikAPI(
    host=os.environ.get("MIKROTIK_HOST", "192.168.88.1"),
    username=os.environ.get("MIKROTIK_USERNAME", "admin"),
    password=os.environ.get("MIKROTIK_PASSWORD", "")
)

# Get active users
active_users = mikrotik_api.get_active_users()

# Add a new user
success = mikrotik_api.add_user(mobile_number, room_number)

# Remove and block a user
mikrotik_api.remove_user(user_id)</code></pre>
    </div>
</div>

<div class="feature-box">
    <div class="feature-title">google_sheets.py</div>
    <p><strong>Purpose:</strong> Authenticates users against Google Sheets database.</p>
    
    <h4>Key Functions:</h4>
    <ul>
        <li><code>_get_credentials()</code>: Loads Google API credentials</li>
        <li><code>get_credential_sheet()</code>: Fetches and caches spreadsheet data</li>
        <li><code>normalize_room_number()</code>: Handles different room number formats</li>
        <li><code>verify_credentials()</code>: Validates mobile/room combinations</li>
    </ul>
    
    <h4>Room Number Normalization:</h4>
    <p>Handles multiple formats like:</p>
    <ul>
        <li>R0/r0/r 0 (Room 0)</li>
        <li>F1/f1/f 1 (Floor 1)</li>
        <li>1 Dorm/dormitory/1dorm (Dormitory 1)</li>
    </ul>
    
    <div class="highlight">
    <div class="code-filename">google_sheets.py</div>
    <pre><code>def verify_credentials(mobile_number, room_number):
    """Verify mobile and room number against Google Sheet"""
    sheet_data = get_credential_sheet()
    normalized_room = normalize_room_number(room_number)
    
    # Search for matching mobile and room number
    for row in sheet_data:
        if (len(row) >= 2 and 
            str(row[0]).strip() == mobile_number and 
            normalize_room_number(str(row[1])) == normalized_room):
            return True
    
    return False</code></pre>
    </div>
</div>

<div class="feature-box">
    <div class="feature-title">convert_to_pdf.py</div>
    <p><strong>Purpose:</strong> Generates PDF documentation from Markdown.</p>
    
    <h4>Features:</h4>
    <ul>
        <li>Converts the MikroTik setup guide to PDF</li>
        <li>Preserves formatting and images</li>
        <li>Uses WeasyPrint for high-quality PDF rendering</li>
    </ul>
</div>

## 3. User Authentication Flow

<div class="feature-box">
    <div class="feature-title">Guest Authentication</div>
    <ol>
        <li>User enters mobile number and room number in login form</li>
        <li><code>app.py:login()</code> receives form data</li>
        <li>System checks for blocked devices by MAC address</li>
        <li><code>google_sheets.py:verify_credentials()</code> validates against Google Sheet</li>
        <li>If valid, user is created or updated in database</li>
        <li><code>mikrotik.py:add_user()</code> connects user to WiFi</li>
        <li>Session is created to track login</li>
    </ol>
    
    <div class="note">
        <strong>Note:</strong> Google Sheets validation ensures only hotel guests can connect, with mobile numbers matching room assignments.
    </div>
</div>

<div class="feature-box">
    <div class="feature-title">Special User Authentication (Staff/Family/Friends)</div>
    <ol>
        <li>User enters mobile number and password in same login form</li>
        <li><code>app.py:login()</code> recognizes user as special by <code>user_type</code> field</li>
        <li>System validates password directly from database, not Google Sheets</li>
        <li>Login session is created and tracked in database</li>
        <li>User preferences and permissions applied based on user type</li>
    </ol>
    
    <div class="success">
        <strong>Feature Highlight:</strong> This allows hotel staff, family members, and friends to have permanent access using custom credentials rather than temporary room assignments.
    </div>
</div>

<div class="feature-box">
    <div class="feature-title">Admin Authentication</div>
    <ol>
        <li>Admin navigates to /admin/login</li>
        <li>Credentials validated against environment variables:
            <ul>
                <li><code>ADMIN_USERNAME</code> (default: "admin")</li>
                <li><code>ADMIN_PASSWORD</code> (default: "admin123")</li>
            </ul>
        </li>
        <li>Upon successful login, admin session created</li>
        <li><code>@admin_required</code> decorator protects admin routes</li>
    </ol>
    
    <div class="warning">
        <strong>Security Note:</strong> For production, always change the default admin credentials by setting the environment variables.
    </div>
</div>

## 4. Admin Panel Features

<div class="feature-box">
    <div class="feature-title">Dashboard</div>
    <p><strong>File:</strong> <code>templates/admin.html</code></p>
    <p><strong>Purpose:</strong> Provides overview of network status</p>
    
    <h4>Key Components:</h4>
    <ul>
        <li>Real-time active user count</li>
        <li>Data usage statistics</li>
        <li>Connected device list with disconnect options</li>
        <li>Login session history</li>
    </ul>
    
    <h4>JavaScript Integration:</h4>
    <ul>
        <li>Chart.js for usage graphs</li>
        <li>AJAX polling for real-time updates</li>
    </ul>
</div>

<div class="feature-box">
    <div class="feature-title">User Management</div>
    <p><strong>File:</strong> <code>templates/admin_users.html</code></p>
    <p><strong>Purpose:</strong> View and manage regular guests</p>
    
    <h4>Features:</h4>
    <ul>
        <li>List all users from Google Sheets</li>
        <li>View registration timestamps</li>
        <li>See session counts per user</li>
    </ul>
</div>

<div class="feature-box">
    <div class="feature-title">Special User Management</div>
    <p><strong>File:</strong> <code>templates/admin_manage_users.html</code></p>
    <p><strong>Purpose:</strong> Add and manage special users with custom credentials</p>
    
    <h4>Features:</h4>
    <ul>
        <li>Create staff, family, and friend accounts</li>
        <li>Set custom passwords (not room numbers)</li>
        <li>Block/unblock users</li>
        <li>Delete user accounts</li>
        <li>Tabbed interface for filtering user types</li>
    </ul>
    
    <div class="highlight">
    <div class="code-filename">app.py (Special User Management)</div>
    <pre><code>@app.route('/admin/add-user', methods=['POST'])
@admin_required
def admin_add_user():
    """Add a new special user (staff, family, friend)"""
    mobile_number = request.form.get('mobile_number')
    password = request.form.get('password')
    user_type = request.form.get('user_type', 'guest')
    
    # Create user in database
    user = User(
        mobile_number=mobile_number,
        password=password,
        user_type=user_type,
        is_active=True
    )
    db.session.add(user)
    db.session.commit()
    
    return redirect(url_for('admin_manage_users'))</code></pre>
    </div>
</div>

<div class="feature-box">
    <div class="feature-title">Session Management</div>
    <p><strong>File:</strong> <code>templates/admin_sessions.html</code></p>
    <p><strong>Purpose:</strong> Track user login history</p>
    
    <h4>Features:</h4>
    <ul>
        <li>View login timestamps</li>
        <li>Track session duration</li>
        <li>Monitor data usage</li>
        <li>See connection details (IP/MAC)</li>
    </ul>
</div>

<div class="feature-box">
    <div class="feature-title">Device Blocking</div>
    <p><strong>File:</strong> <code>templates/admin_blocked.html</code></p>
    <p><strong>Purpose:</strong> Manage blocked devices</p>
    
    <h4>Features:</h4>
    <ul>
        <li>View blocked MAC addresses</li>
        <li>See blocking reason and timestamp</li>
        <li>Unblock devices</li>
        <li>Automatic blocking after admin disconnection</li>
    </ul>
    
    <div class="highlight">
    <div class="code-filename">app.py (Device Blocking)</div>
    <pre><code>@app.route('/admin/block-user/<int:user_id>', methods=['POST'])
@admin_required
def admin_block_user(user_id):
    """Block a user"""
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
        logger.error(f"Error blocking user: {str(e)}")
    
    return redirect(url_for('admin_manage_users'))</code></pre>
    </div>
</div>

## 5. Technical Implementation Details

<div class="feature-box">
    <div class="feature-title">Database Schema</div>
    <p><strong>Migration File:</strong> <code>migrations/update_user_table.sql</code></p>
    
    <h4>Key Tables:</h4>
    <ol>
        <li><strong>users</strong>:
            <ul>
                <li>Primary authentication table</li>
                <li>Stores both guests and special users</li>
                <li>Tracks user activity status</li>
            </ul>
        </li>
        <li><strong>login_sessions</strong>:
            <ul>
                <li>Historical record of logins</li>
                <li>Tracks session duration</li>
                <li>Records data usage</li>
            </ul>
        </li>
        <li><strong>blocked_devices</strong>:
            <ul>
                <li>MAC address blacklist</li>
                <li>Blocking reason and admin information</li>
                <li>Active/inactive status</li>
            </ul>
        </li>
    </ol>
</div>

<div class="feature-box">
    <div class="feature-title">Session Management</div>
    <p><strong>Implementation:</strong> Flask's <code>session</code> object</p>
    
    <h4>Key Session Variables:</h4>
    <ul>
        <li><code>user_mobile</code>: Mobile number</li>
        <li><code>user_room</code>: Room number or password</li>
        <li><code>authenticated</code>: Login status</li>
        <li><code>login_time</code>: Timestamp</li>
        <li><code>login_session_id</code>: Database record ID</li>
        <li><code>mac</code>: Device MAC address</li>
        <li><code>ip</code>: Device IP address</li>
    </ul>
</div>

<div class="feature-box">
    <div class="feature-title">Error Handling</div>
    <p><strong>Strategy:</strong> Comprehensive logging and user feedback</p>
    
    <h4>Implementation:</h4>
    <ul>
        <li>Flask flash messages for user feedback</li>
        <li>Detailed exception logging</li>
        <li>Development mode for offline testing</li>
        <li>Graceful degradation when external services unavailable</li>
    </ul>
</div>

<div class="feature-box">
    <div class="feature-title">Security Considerations</div>
    
    <h4>Authentication:</h4>
    <ul>
        <li>MAC address tracking and blocking</li>
        <li>Admin-only routes protection</li>
        <li>Session timeout handling</li>
    </ul>
    
    <h4>Environment Variables:</h4>
    <ul>
        <li><code>DATABASE_URL</code>: PostgreSQL connection</li>
        <li><code>MIKROTIK_*</code>: Router credentials</li>
        <li><code>GOOGLE_CREDENTIALS_*</code>: API authentication</li>
        <li><code>ADMIN_*</code>: Admin panel access</li>
    </ul>
</div>

## 6. Deployment Preparation

<div class="feature-box">
    <div class="feature-title">Required Environment Variables</div>
    
    <table>
        <tr>
            <th>Variable</th>
            <th>Purpose</th>
            <th>Example</th>
        </tr>
        <tr>
            <td><code>DATABASE_URL</code></td>
            <td>PostgreSQL connection string</td>
            <td><code>postgresql://user:pass@host:port/dbname</code></td>
        </tr>
        <tr>
            <td><code>MIKROTIK_HOST</code></td>
            <td>Router IP address</td>
            <td><code>192.168.88.1</code></td>
        </tr>
        <tr>
            <td><code>MIKROTIK_USERNAME</code></td>
            <td>Router admin username</td>
            <td><code>admin</code></td>
        </tr>
        <tr>
            <td><code>MIKROTIK_PASSWORD</code></td>
            <td>Router admin password</td>
            <td><code>password123</code></td>
        </tr>
        <tr>
            <td><code>GOOGLE_CREDENTIALS_JSON</code></td>
            <td>Service account credentials</td>
            <td><code>{"type": "service_account", ...}</code></td>
        </tr>
        <tr>
            <td><code>SPREADSHEET_ID</code></td>
            <td>Google Sheet identifier</td>
            <td><code>1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms</code></td>
        </tr>
        <tr>
            <td><code>ADMIN_USERNAME</code></td>
            <td>Override default admin username</td>
            <td><code>administrator</code></td>
        </tr>
        <tr>
            <td><code>ADMIN_PASSWORD</code></td>
            <td>Override default admin password</td>
            <td><code>secure_password_here</code></td>
        </tr>
        <tr>
            <td><code>DEVELOPMENT_MODE</code></td>
            <td>Enable/disable offline testing mode</td>
            <td><code>true</code> or <code>false</code></td>
        </tr>
    </table>
</div>

<div class="feature-box">
    <div class="feature-title">Server Configuration</div>
    
    <h4>Flask Application:</h4>
    <ul>
        <li>Served via Gunicorn on port 5000</li>
        <li>Binds to 0.0.0.0 for external access</li>
        <li>Uses Werkzeug ProxyFix for proper URL generation</li>
    </ul>
    
    <h4>Database:</h4>
    <ul>
        <li>PostgreSQL with connection pooling</li>
        <li>Connection recycling every 300 seconds</li>
        <li>Pre-ping to verify connections</li>
    </ul>
    
    <h4>Static Files:</h4>
    <ul>
        <li>Bootstrap CSS for styling</li>
        <li>Admin JavaScript files for dashboard interaction</li>
        <li>Custom CSS for UI enhancements</li>
    </ul>
</div>

## 7. Additional Documentation

<div class="feature-box">
    <div class="feature-title">MikroTik Router Setup Guide</div>
    <p><strong>Files:</strong></p>
    <ul>
        <li><code>mikrotik_setup_guide.md</code>: Markdown source</li>
        <li><code>mikrotik_setup_guide.pdf</code>: Generated PDF</li>
    </ul>
    
    <h4>Contents:</h4>
    <ul>
        <li>Step-by-step router configuration</li>
        <li>Hotspot setup instructions</li>
        <li>Captive portal integration</li>
        <li>Security best practices</li>
        <li>Troubleshooting guide</li>
    </ul>
</div>

---

<div style="text-align: center; margin-top: 50px; color: #666;">
    <p>This comprehensive system provides a complete solution for hotel/dormitory WiFi authentication with Google Sheets integration and advanced user management capabilities.</p>
    <p>© 2025 MikroTik Captive Portal System</p>
</div>