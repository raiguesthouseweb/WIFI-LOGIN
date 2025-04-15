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
    
    # Print configuration settings for debugging
    logger.info(f"Google Sheet Configuration - SPREADSHEET_ID: {SPREADSHEET_ID}, SHEET_NAME: {SHEET_NAME}")
    
    # Check for credentials
    if not os.path.exists(GOOGLE_CREDENTIALS_FILE) and not os.environ.get('GOOGLE_CREDENTIALS_JSON'):
        logger.error("No Google credentials found - neither file nor environment variable")
        logger.info("Expected credentials file path: " + os.path.abspath(GOOGLE_CREDENTIALS_FILE))
        return []
    
    # Return cached data if available and not expired
    if not force_refresh and _sheet_data is not None and (current_time - _last_refresh_time) < SHEET_CACHE_TIMEOUT:
        logger.info(f"Using cached sheet data ({len(_sheet_data)} rows, cache age: {(current_time - _last_refresh_time):.1f}s)")
        return _sheet_data
    
    logger.info("Fetching fresh data from Google Sheets...")
    
    try:
        credentials = _get_credentials()
        if not credentials:
            logger.error("Failed to obtain Google credentials despite files existing")
            return []
        
        service = build('sheets', 'v4', credentials=credentials)
        sheet = service.spreadsheets()
        
        # Request specific columns for better performance
        range_name = f"{SHEET_NAME}!A:C"  # We need columns A (Name), B (Mobile), C (Room)
        logger.info(f"Requesting sheet range: {range_name}")
        
        # Call the Sheets API
        result = sheet.values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.warning('No data found in the Google Sheet')
            return []
        
        # Log sheet structure for debugging
        if len(values) > 0:
            logger.info(f"Sheet has {len(values)} rows")
            logger.info(f"First row (likely headers): {values[0]}")
            
            # Skip header row if present
            has_header = False
            if values[0][0].lower() in ["name", "guest name", "guest"]:
                has_header = True
                logger.info("Header row detected, will skip in processing")
            
            if has_header:
                data_rows = values[1:]
            else:
                data_rows = values
                
            logger.info(f"Total data rows (excluding header): {len(data_rows)}")
            
            # Additional validation
            if len(data_rows) > 0:
                if len(data_rows[0]) < 3:
                    logger.warning(f"First data row has fewer than 3 columns: {data_rows[0]}")
                else:
                    logger.info(f"Sample data format OK: {len(data_rows[0])} columns in first row")
            
            _sheet_data = data_rows
            _last_refresh_time = current_time
            return _sheet_data
        else:
            logger.warning("Sheet returned empty data")
            return []
    
    except HttpError as e:
        logger.error(f"Google Sheets API error: {str(e)}")
        # More specific error messages for common issues
        if "404" in str(e):
            logger.error(f"Sheet not found. Check SPREADSHEET_ID: {SPREADSHEET_ID}")
        elif "403" in str(e):
            logger.error("Permission denied. Make sure the service account has access to the sheet.")
        return []
    
    except Exception as e:
        logger.error(f"Error fetching sheet data: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return []

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
    # Clean input immediately
    if not mobile_number or not room_number:
        logger.warning("Missing mobile number or room number")
        return False
    
    logger.info(f"Validating credentials - Mobile: {mobile_number}, Room: {room_number}")
    
    # Standardize mobile number format
    mobile_number = mobile_number.strip()
    if mobile_number.startswith('+'):
        mobile_number = mobile_number[1:]
    
    # Normalize room number format 
    normalized_input_room = normalize_room_number(room_number)
    logger.info(f"Normalized room number: {room_number} -> {normalized_input_room}")
    
    try:
        # Get sheet data with added debugging
        logger.info("Fetching Google Sheet data for validation...")
        sheet_data = get_credential_sheet()
        
        if not sheet_data:
            logger.warning("No sheet data available - cannot validate credentials")
            # For development/testing, return True to allow login
            # In production, you would return False here
            return True
        
        logger.info(f"Loaded {len(sheet_data)} rows from sheet for validation")
        
        # Log first few entries from sheet for debugging (without exposing all data)
        if len(sheet_data) > 0:
            sample_size = min(3, len(sheet_data))
            logger.info(f"Sample data (first {sample_size} rows):")
            for i in range(sample_size):
                if i < len(sheet_data):
                    row = sheet_data[i]
                    # Mask mobile numbers for privacy in logs
                    if len(row) >= 2:
                        masked_mobile = "**" + row[1][-4:] if len(row[1]) > 4 else row[1]
                        logger.info(f"Row {i}: {row[0][:10]}..., Mobile: {masked_mobile}, Room: {row[2] if len(row) > 2 else 'N/A'}")
        
        # Check each row for a match
        match_found = False
        mobile_matches = []
        room_matches = []
        
        for i, row in enumerate(sheet_data):
            # Skip if row doesn't have enough data
            if len(row) < 3:
                logger.warning(f"Row {i} has incomplete data: {row}")
                continue
            
            # Extract and clean data
            sheet_mobile = str(row[1]).strip()
            sheet_room = str(row[2]).strip()
            
            # Remove country code if present
            if sheet_mobile.startswith('+'):
                sheet_mobile = sheet_mobile[1:]
            
            # Normalize room number for comparison
            normalized_sheet_room = normalize_room_number(sheet_room)
            
            # Track partial matches for better error messages
            if sheet_mobile == mobile_number:
                mobile_matches.append((sheet_room, normalized_sheet_room))
            
            if normalized_sheet_room == normalized_input_room:
                room_matches.append(sheet_mobile)
            
            # Check for exact match
            if sheet_mobile == mobile_number and normalized_sheet_room == normalized_input_room:
                logger.info(f"MATCH FOUND: Mobile: {mobile_number}, Room: {normalized_input_room}")
                match_found = True
                break
        
        # Detailed log if no match found
        if not match_found:
            if mobile_matches:
                logger.info(f"Mobile number {mobile_number} found, but with different rooms: {mobile_matches}")
            if room_matches:
                logger.info(f"Room {normalized_input_room} found, but with different mobile numbers: {room_matches}")
            if not mobile_matches and not room_matches:
                logger.info(f"No matches found for either mobile or room")
            
            logger.warning(f"Validation failed for mobile: {mobile_number}, room: {normalized_input_room}")
            return False
        
        return match_found
    
    except Exception as e:
        logger.error(f"Error during credential verification: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # In production environment, return False on errors
        # For development/testing, allowing access for now
        return True
