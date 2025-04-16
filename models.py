from datetime import datetime
from main import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    mobile_number = db.Column(db.String(20), unique=True, nullable=False)
    room_number = db.Column(db.String(20), nullable=True)  # Can be null for non-guest users
    password = db.Column(db.String(100), nullable=True)    # For staff, family, and friends
    user_type = db.Column(db.String(20), default='guest')  # guest, staff, family, friend
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    login_sessions = db.relationship('LoginSession', backref='user', lazy=True)
    
    def __repr__(self):
        return f'<User {self.mobile_number} ({self.user_type})>'

class LoginSession(db.Model):
    __tablename__ = 'login_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    mac_address = db.Column(db.String(17), nullable=True)
    login_time = db.Column(db.DateTime, default=datetime.utcnow)
    logout_time = db.Column(db.DateTime, nullable=True)
    bytes_in = db.Column(db.BigInteger, default=0)
    bytes_out = db.Column(db.BigInteger, default=0)
    
    def __repr__(self):
        return f'<LoginSession {self.id} - User {self.user_id}>'

class BlockedDevice(db.Model):
    __tablename__ = 'blocked_devices'
    
    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.String(17), unique=True, nullable=False)
    mobile_number = db.Column(db.String(20), nullable=True)
    reason = db.Column(db.String(255), nullable=True)
    blocked_at = db.Column(db.DateTime, default=datetime.utcnow)
    blocked_by = db.Column(db.String(50), nullable=True)  # Admin username or system
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<BlockedDevice {self.mac_address}>'

class GoogleCredential(db.Model):
    __tablename__ = 'google_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    spreadsheet_id = db.Column(db.String(255), nullable=False)
    credentials_json = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<GoogleCredential {self.id}>'