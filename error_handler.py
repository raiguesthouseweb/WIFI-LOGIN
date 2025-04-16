#!/usr/bin/env python3
"""
Intelligent Error Handler for MikroTik Captive Portal System

This module provides structured error handling with helpful suggestions
for common error scenarios in the application.
"""
import logging
import os
from functools import wraps
from flask import flash, redirect, url_for, render_template, request, jsonify

# Configure logging
logger = logging.getLogger(__name__)

class ErrorCategory:
    """Error categories for organizing different types of errors"""
    MIKROTIK = "mikrotik"
    GOOGLE_SHEETS = "google_sheets"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    GENERAL = "general"

class ErrorHandler:
    """
    Main error handler class that provides detailed error messages and suggestions
    for different error scenarios
    """
    
    # Mapping of error types to user-friendly messages and suggestions
    ERROR_MESSAGES = {
        ErrorCategory.MIKROTIK: {
            "connection_timeout": {
                "title": "Router Connection Error",
                "message": "Unable to connect to the MikroTik router. The connection has timed out.",
                "suggestions": [
                    "Check if the router is powered on and accessible on the network.",
                    "Verify the router IP address in your environment settings.",
                    "Ensure the router username and password are correct.",
                    "Check your network firewall settings to allow connections to the router API port."
                ],
                "admin_note": "This is often caused by incorrect MIKROTIK_HOST, MIKROTIK_USERNAME, or MIKROTIK_PASSWORD environment variables.",
                "is_critical": True
            },
            "authentication_failed": {
                "title": "Router Authentication Failed",
                "message": "Failed to authenticate with the MikroTik router.",
                "suggestions": [
                    "Verify that the router admin credentials are correct.",
                    "Make sure the router has API access enabled.",
                    "Check if the router's API port (8728) is accessible."
                ],
                "admin_note": "Check MIKROTIK_USERNAME and MIKROTIK_PASSWORD environment variables.",
                "is_critical": True
            },
            "api_error": {
                "title": "Router API Error",
                "message": "An error occurred while communicating with the router API.",
                "suggestions": [
                    "The router might be running an unsupported RouterOS version.",
                    "Try rebooting the router if the problem persists."
                ],
                "admin_note": "Review the specific API error in the logs for more details.",
                "is_critical": False
            }
        },
        ErrorCategory.GOOGLE_SHEETS: {
            "authentication_failed": {
                "title": "Google Sheets Authentication Error",
                "message": "Failed to authenticate with Google Sheets API.",
                "suggestions": [
                    "Make sure the Google service account credentials are valid.",
                    "Check if the spreadsheet exists and is accessible to the service account."
                ],
                "admin_note": "Verify GOOGLE_CREDENTIALS_JSON environment variable or credentials.json file.",
                "is_critical": True
            },
            "spreadsheet_not_found": {
                "title": "Spreadsheet Not Found",
                "message": "The specified Google spreadsheet could not be found.",
                "suggestions": [
                    "Check if the spreadsheet ID is correct.",
                    "Ensure the spreadsheet has been shared with the service account email."
                ],
                "admin_note": "Verify SPREADSHEET_ID environment variable.",
                "is_critical": True
            },
            "api_rate_limit": {
                "title": "Google API Rate Limit",
                "message": "Google Sheets API rate limit exceeded.",
                "suggestions": [
                    "The system is temporarily retrieving too much data.",
                    "Try again in a few minutes.",
                    "The issue should resolve automatically."
                ],
                "admin_note": "Consider implementing exponential backoff for Google API calls.",
                "is_critical": False
            }
        },
        ErrorCategory.DATABASE: {
            "connection_error": {
                "title": "Database Connection Error",
                "message": "Unable to connect to the database.",
                "suggestions": [
                    "This is a temporary system error.",
                    "Try refreshing the page or try again later.",
                    "If the problem persists, contact technical support."
                ],
                "admin_note": "Check DATABASE_URL environment variable and database server status.",
                "is_critical": True
            },
            "query_error": {
                "title": "Database Query Error",
                "message": "An error occurred while processing your request in the database.",
                "suggestions": [
                    "This is usually a temporary issue.",
                    "Try again in a few moments.",
                    "If the error persists, contact the administrator."
                ],
                "admin_note": "Check the specific SQL error in the logs.",
                "is_critical": False
            }
        },
        ErrorCategory.AUTHENTICATION: {
            "invalid_credentials": {
                "title": "Invalid Login Credentials",
                "message": "The mobile number or room number is incorrect.",
                "suggestions": [
                    "Make sure you're entering your mobile number without the country code.",
                    "Double-check your room number format (e.g., R0, F1, 1 Dorm).",
                    "If you're a guest, verify your details with the reception.",
                    "For staff/family/friends, contact the administrator if you've forgotten your password."
                ],
                "admin_note": "User might need to be added to the system or Google Sheet.",
                "is_critical": False
            },
            "account_blocked": {
                "title": "Account Blocked",
                "message": "This account or device has been blocked.",
                "suggestions": [
                    "Your account or device has been blocked by the administrator.",
                    "Please contact the reception or hotel staff for assistance.",
                    "Provide your mobile number and room details when seeking help."
                ],
                "admin_note": "Check blocked_devices table for the specific reason.",
                "is_critical": True
            }
        },
        ErrorCategory.NETWORK: {
            "client_timeout": {
                "title": "Network Timeout",
                "message": "The request timed out due to network issues.",
                "suggestions": [
                    "Check your device's internet connection.",
                    "Try moving closer to the WiFi access point.",
                    "Restart your device's WiFi connection."
                ],
                "admin_note": "This could be a client-side network issue.",
                "is_critical": False
            }
        },
        ErrorCategory.GENERAL: {
            "unknown_error": {
                "title": "Unexpected Error",
                "message": "An unexpected error occurred.",
                "suggestions": [
                    "Try refreshing the page.",
                    "Clear your browser cache and cookies.",
                    "Try again in a few minutes.",
                    "If the problem persists, contact technical support."
                ],
                "admin_note": "Check the logs for the specific error details.",
                "is_critical": False
            },
            "maintenance_mode": {
                "title": "System Maintenance",
                "message": "The system is currently undergoing maintenance.",
                "suggestions": [
                    "Please try again later.",
                    "Maintenance is usually completed within 30 minutes."
                ],
                "admin_note": "This is shown during scheduled maintenance periods.",
                "is_critical": True
            }
        }
    }
    
    @classmethod
    def get_error_details(cls, category, error_type):
        """
        Get the error details for a specific category and type
        
        Args:
            category: The error category (from ErrorCategory)
            error_type: The specific error type within that category
            
        Returns:
            dict: The error details or a default unknown error if not found
        """
        try:
            return cls.ERROR_MESSAGES[category][error_type]
        except KeyError:
            logger.warning(f"Unknown error type requested: {category}/{error_type}")
            return cls.ERROR_MESSAGES[ErrorCategory.GENERAL]["unknown_error"]
    
    @classmethod
    def format_error(cls, category, error_type, additional_info=None, for_api=False):
        """
        Format an error message with suggestions based on the error type
        
        Args:
            category: The error category
            error_type: The specific error type
            additional_info: Any additional context-specific information
            for_api: Whether this is for an API response (JSON) or UI (flash)
            
        Returns:
            dict: Formatted error details for API response or UI rendering
        """
        error_details = cls.get_error_details(category, error_type)
        
        # Add the additional info if provided
        message = error_details["message"]
        if additional_info:
            message = f"{message} {additional_info}"
        
        # For development mode, include admin note
        is_dev_mode = os.environ.get("DEVELOPMENT_MODE", "false").lower() == "true"
        admin_note = error_details.get("admin_note", "") if is_dev_mode else ""
        
        formatted_error = {
            "title": error_details["title"],
            "message": message,
            "suggestions": error_details["suggestions"],
            "admin_note": admin_note,
            "is_critical": error_details.get("is_critical", False)
        }
        
        # Log the error
        log_message = f"[{category.upper()}] {error_details['title']}: {message}"
        if error_details.get("is_critical", False):
            logger.error(log_message)
        else:
            logger.warning(log_message)
        
        return formatted_error
    
    @classmethod
    def flash_error(cls, category, error_type, additional_info=None):
        """
        Flash an error message for displaying in the UI
        
        Args:
            category: The error category
            error_type: The specific error type
            additional_info: Any additional context-specific information
        """
        error = cls.format_error(category, error_type, additional_info)
        flash_message = f"{error['title']}: {error['message']}"
        flash(flash_message, 'error')
        
        # Add suggestions as separate flash messages
        for suggestion in error['suggestions']:
            flash(suggestion, 'suggestion')
        
        # If in development mode and there's an admin note, flash it
        if error['admin_note']:
            flash(f"Admin note: {error['admin_note']}", 'admin-note')
    
    @classmethod
    def api_error(cls, category, error_type, additional_info=None, status_code=400):
        """
        Return a JSON error response for API endpoints
        
        Args:
            category: The error category
            error_type: The specific error type
            additional_info: Any additional context-specific information
            status_code: The HTTP status code to return
            
        Returns:
            Response: A Flask JSON response with error details
        """
        error = cls.format_error(category, error_type, additional_info, for_api=True)
        
        response = {
            "success": False,
            "error": {
                "title": error["title"],
                "message": error["message"],
                "suggestions": error["suggestions"]
            }
        }
        
        # Include admin_note only in development mode
        if error['admin_note']:
            response["error"]["admin_note"] = error["admin_note"]
        
        return jsonify(response), status_code
    
    @classmethod
    def error_page(cls, category, error_type, additional_info=None, status_code=500):
        """
        Render an error page with detailed information
        
        Args:
            category: The error category
            error_type: The specific error type
            additional_info: Any additional context-specific information
            status_code: The HTTP status code
            
        Returns:
            Response: A rendered error page
        """
        error = cls.format_error(category, error_type, additional_info)
        
        # Determine if we should show a critical error page or a less severe one
        template = 'error_critical.html' if error['is_critical'] else 'error.html'
        
        return render_template(
            template,
            title=error["title"],
            message=error["message"],
            suggestions=error["suggestions"],
            admin_note=error["admin_note"],
            status_code=status_code
        ), status_code


def handle_errors(f):
    """
    Decorator for route handlers to catch and process exceptions
    
    Args:
        f: The function to decorate
        
    Returns:
        The decorated function with error handling
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Unhandled exception in {f.__name__}: {str(e)}")
            
            # For API endpoints, return JSON response
            if request.path.startswith('/api/'):
                return ErrorHandler.api_error(
                    ErrorCategory.GENERAL, 
                    "unknown_error", 
                    f"Error details: {str(e)}" if os.environ.get("DEVELOPMENT_MODE", "false").lower() == "true" else None
                )
            
            # Otherwise, flash message and redirect to appropriate page
            ErrorHandler.flash_error(
                ErrorCategory.GENERAL, 
                "unknown_error",
                f"Error details: {str(e)}" if os.environ.get("DEVELOPMENT_MODE", "false").lower() == "true" else None
            )
            
            # Determine redirect based on error and current user state
            if 'authenticated' in request.cookies and request.cookies['authenticated'] == 'true':
                return redirect(url_for('index'))
            else:
                return redirect(url_for('login'))
    
    return decorated_function