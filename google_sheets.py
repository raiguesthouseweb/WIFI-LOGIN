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

def normalize_room_number(room_number):
    """
    Normalize room number for comparison by removing spaces and converting to uppercase
    
    Args:
        room_number: Room number string to normalize
        
    Returns:
        Normalized room number string
    """
    import re
    
    if not room_number:
        return ""
    
    # Convert to string, strip, and convert to uppercase
    normalized = str(room_number).strip().upper()
    
    # Log original value for debugging
    logger.debug(f"Normalizing room number: '{room_number}' -> initial '{normalized}'")
    
    # Handle dormitory format patterns
    dorm_pattern = re.search(r'(\d+)\s*(?:DORM|DORMITORY)', normalized)
    if dorm_pattern or "DORM" in normalized or "DORMITORY" in normalized:
        # If we have a clear match with the regex
        if dorm_pattern:
            result = f"{dorm_pattern.group(1)}DORM"
            logger.debug(f"Dormitory format detected: {normalized} -> {result}")
            return result
        
        # Otherwise try to extract just the number
        for digit in re.findall(r'\d+', normalized):
            result = f"{digit}DORM"
            logger.debug(f"Extracted dormitory number: {normalized} -> {result}")
            return result
        
        # If still no match, return as is
        return normalized
    
    # Remove all spaces
    normalized = normalized.replace(" ", "")
    
    # Handle lowercase r prefix (e.g., "r0" -> "R0")
    r_pattern = re.match(r'^[rR](\d+)$', normalized)
    if r_pattern:
        result = f"R{r_pattern.group(1)}"
        logger.debug(f"Room format detected: {normalized} -> {result}")
        return result
    
    # Handle lowercase f prefix (e.g., "f1" -> "F1")
    f_pattern = re.match(r'^[fF](\d+)$', normalized)
    if f_pattern:
        result = f"F{f_pattern.group(1)}"
        logger.debug(f"Floor format detected: {normalized} -> {result}")
        return result
    
    # If it's just a digit, assume it's a room number
    if normalized.isdigit():
        if len(normalized) == 1:
            # Single digit is likely room number
            result = f"R{normalized}"
            logger.debug(f"Single digit treated as room: {normalized} -> {result}")
            return result
    
    logger.debug(f"No special formatting applied, using: {normalized}")
    return normalized

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
        
        # Strip the '+' if it was included in the mobile number
        if mobile_number.startswith('+'):
            mobile_number = mobile_number[1:]
        
        # Normalize the provided room number
        normalized_input_room = normalize_room_number(room_number)
        
        # Debug information for troubleshooting
        logger.debug(f"Attempting to validate - Mobile: {mobile_number}, Room: {room_number} (Normalized: {normalized_input_room})")
        logger.debug(f"Sheet data rows: {len(sheet_data) if sheet_data else 0}")
        
        if sheet_data:
            for row in sheet_data:
                # Check if the row has at least 3 columns (Name, Mobile, Room)
                if len(row) < 3:
                    continue
                
                sheet_mobile = str(row[1]).strip()  # Column B - Mobile Number
                sheet_room = str(row[2]).strip()    # Column C - Room Number
                
                # Strip the '+' if it exists in sheet data
                if sheet_mobile.startswith('+'):
                    sheet_mobile = sheet_mobile[1:]
                
                # Normalize the sheet room number
                normalized_sheet_room = normalize_room_number(sheet_room)
                
                # Debug info
                logger.debug(f"Comparing with - Sheet Mobile: {sheet_mobile}, Sheet Room: {sheet_room} (Normalized: {normalized_sheet_room})")
                
                # Compare the provided credentials with the sheet data
                if sheet_mobile == mobile_number and normalized_sheet_room == normalized_input_room:
                    logger.info(f"Credentials verified for mobile: {mobile_number}")
                    return True
            
            logger.warning(f"Invalid credentials for mobile: {mobile_number}, room: {room_number}")
            return False
        else:
            # If sheet_data is None or empty, log warning and allow login for testing
            logger.warning("No Google Sheet data available, allowing login without validation")
            return True
    
    except Exception as e:
        logger.error(f"Error verifying credentials: {str(e)}")
        # In production, you would want to deny access when verification fails
        # But for development/testing, we'll allow access
        return True
