import os

# Google API
GOOGLE_CREDENTIALS_FILE = os.environ.get('GOOGLE_CREDENTIALS_FILE', 'attached_assets/guestloginproject-8d27f814c0aa.json')
SPREADSHEET_ID = os.environ.get('SPREADSHEET_ID', '176lp2Z2usUXj7x3guMmTnMikoSqkXQrXw5jLfYguEq4')
SHEET_NAME = os.environ.get('SHEET_NAME', 'Sheet1')

# MikroTik settings
MIKROTIK_HOST = os.environ.get('MIKROTIK_HOST', '192.168.88.1') 
MIKROTIK_PORT = int(os.environ.get('MIKROTIK_PORT', 8728))
MIKROTIK_USERNAME = os.environ.get('MIKROTIK_USERNAME', 'admin')
MIKROTIK_PASSWORD = os.environ.get('MIKROTIK_PASSWORD', '')

# Admin credentials
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

# Cache settings
SHEET_CACHE_TIMEOUT = int(os.environ.get('SHEET_CACHE_TIMEOUT', 300))  # 5 minutes
