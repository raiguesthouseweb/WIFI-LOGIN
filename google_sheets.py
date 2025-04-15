import os
import logging
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from config import GOOGLE_CREDENTIALS_FILE, SPREADSHEET_ID, SHEET_NAME, SHEET_CACHE_TIMEOUT

# Set up logging
logger = logging.getLogger(__name__)

# Cache for sheet data
_sheet_data = None
_last_refresh_time = 0

def _get_credentials():
    """
    Get Google API credentials from service account file or environment variable
    """
    try:
        # First try to get credentials from file
        if os.path.exists(GOOGLE_CREDENTIALS_FILE):
            return service_account.Credentials.from_service_account_file(
                GOOGLE_CREDENTIALS_FILE,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
        
        # If file doesn't exist, try environment variable
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if creds_json:
            creds_info = json.loads(creds_json)
            return service_account.Credentials.from_service_account_info(
                creds_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
            )
        
        # If neither exists, log error
        logger.error("No Google credentials found")
        return None
    
    except Exception as e:
        logger.error(f"Error loading Google credentials: {str(e)}")
        return None

def get_credential_sheet(force_refresh=False):
    """
    Fetch data from Google Sheets
    
    Args:
        force_refresh: If True, force refresh the cache
        
    Returns:
        List of rows from the sheet
    """
    global _sheet_data, _last_refresh_time
    
    current_time = time.time()
    
    # Return cached data if available and not expired
    if not force_refresh and _sheet_data is not None and (current_time - _last_refresh_time) < SHEET_CACHE_TIMEOUT:
        return _sheet_data
    
    try:
        credentials = _get_credentials()
        if not credentials:
            logger.error("Failed to obtain Google credentials")
            return []
        
        service = build('sheets', 'v4', credentials=credentials)
        
        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{SHEET_NAME}!A:E"  # Get all columns A through E
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.warning('No data found in the Google Sheet')
            _sheet_data = []
        else:
            # Skip header row if present
            if values and len(values) > 0 and "Name" in values[0][0]:
                values = values[1:]
            _sheet_data = values
        
        _last_refresh_time = current_time
        return _sheet_data
    
    except HttpError as e:
        logger.error(f"Google Sheets API error: {str(e)}")
        if _sheet_data is None:  # Only initialize to empty if we don't have previous data
            _sheet_data = []
        return _sheet_data
    
    except Exception as e:
        logger.error(f"Error fetching sheet data: {str(e)}")
        if _sheet_data is None:
            _sheet_data = []
        return _sheet_data

def verify_credentials(mobile_number, room_number):
    """
    Verify the provided mobile number and room number against the Google Sheet
    
    Args:
        mobile_number: The mobile number to verify
        room_number: The room number to verify
        
    Returns:
        Boolean indicating whether the credentials are valid
    """
    try:
        sheet_data = get_credential_sheet()
        
        for row in sheet_data:
            # Check if the row has at least 3 columns (Name, Mobile, Room)
            if len(row) < 3:
                continue
            
            sheet_mobile = str(row[1]).strip()  # Column B - Mobile Number
            sheet_room = str(row[2]).strip()    # Column C - Room Number
            
            # Compare the provided credentials with the sheet data
            if sheet_mobile == mobile_number and sheet_room == room_number:
                logger.debug(f"Credentials verified for mobile: {mobile_number}")
                return True
        
        logger.debug(f"Invalid credentials for mobile: {mobile_number}")
        return False
    
    except Exception as e:
        logger.error(f"Error verifying credentials: {str(e)}")
        return False
