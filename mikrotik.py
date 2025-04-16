import logging
import routeros_api
import time
import os
import socket
from config import MIKROTIK_HOST, MIKROTIK_PORT, MIKROTIK_USERNAME, MIKROTIK_PASSWORD
from error_handler import ErrorHandler, ErrorCategory

# Set up logging
logger = logging.getLogger(__name__)

class MikroTikAPI:
    """
    A class to handle interactions with MikroTik router API
    """
    
    def __init__(self, host=MIKROTIK_HOST, port=MIKROTIK_PORT, username=MIKROTIK_USERNAME, password=MIKROTIK_PASSWORD):
        """
        Initialize the MikroTik API connection
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connection = None
        
    def connect(self):
        """
        Establish a connection to the MikroTik router
        """
        if self.connection is None:
            try:
                # Create a connection to the router
                self.connection = routeros_api.RouterOsApiPool(
                    self.host,
                    username=self.username,
                    password=self.password,
                    port=self.port,
                    plaintext_login=True
                )
                api = self.connection.get_api()
                return api
            except socket.timeout:
                logger.error("Failed to connect to MikroTik router: timed out")
                self.connection = None
                raise ConnectionError(
                    ErrorHandler.format_error(
                        ErrorCategory.MIKROTIK, 
                        "connection_timeout",
                        f"Host: {self.host}, Port: {self.port}"
                    )
                )
            except routeros_api.exceptions.RouterOsApiConnectionError as e:
                if "invalid user name or password" in str(e).lower():
                    logger.error(f"Failed to authenticate with MikroTik router: {str(e)}")
                    self.connection = None
                    raise ConnectionError(
                        ErrorHandler.format_error(
                            ErrorCategory.MIKROTIK, 
                            "authentication_failed"
                        )
                    )
                else:
                    logger.error(f"Failed to connect to MikroTik router: {str(e)}")
                    self.connection = None
                    raise ConnectionError(
                        ErrorHandler.format_error(
                            ErrorCategory.MIKROTIK, 
                            "connection_timeout"
                        )
                    )
            except Exception as e:
                logger.error(f"Failed to connect to MikroTik router: {str(e)}")
                self.connection = None
                raise ConnectionError(
                    ErrorHandler.format_error(
                        ErrorCategory.MIKROTIK, 
                        "api_error",
                        f"Error details: {str(e)}"
                    )
                )
        else:
            return self.connection.get_api()
    
    def disconnect(self):
        """
        Close the connection to the MikroTik router
        """
        if self.connection:
            try:
                self.connection.disconnect()
            except Exception:
                pass
            finally:
                self.connection = None
    
    def get_active_users(self):
        """
        Get a list of active users from the router's hotspot
        """
        # Check if we're in development mode - if so, return empty list without contacting router
        if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true':
            logger.info("Development mode: Returning empty active users list without contacting router")
            # Return sample data in development mode
            return []
            
        try:
            api = self.connect()
            hotspot_active = api.get_resource('/ip/hotspot/active')
            active_users = hotspot_active.get()
            
            # Format the users for display
            users = []
            for user in active_users:
                users.append({
                    'id': user.get('id', ''),
                    'user': user.get('user', ''),  # This should be the mobile number
                    'address': user.get('address', ''),
                    'mac_address': user.get('mac-address', ''),
                    'uptime': user.get('uptime', ''),
                    'bytes_in': user.get('bytes-in', '0'),
                    'bytes_out': user.get('bytes-out', '0')
                })
            
            return users
        except socket.timeout:
            error_info = ErrorHandler.format_error(
                ErrorCategory.MIKROTIK, 
                "connection_timeout"
            )
            logger.error(f"Error getting active users: {error_info['title']} - {error_info['message']}")
            # Return empty list instead of raising exception to avoid breaking the admin page
            return []
        except ConnectionError as e:
            # This is likely from our own error handler in connect()
            logger.error(f"Error getting active users: {str(e)}")
            return []
        except Exception as e:
            error_info = ErrorHandler.format_error(
                ErrorCategory.MIKROTIK, 
                "api_error",
                f"Error details: {str(e)}"
            )
            logger.error(f"Error getting active users: {error_info['title']} - {error_info['message']}")
            # Return empty list instead of raising exception to avoid breaking the admin page
            return []
    
    def add_user(self, username, password):
        """
        Add a user to the hotspot users (if needed) and authenticate them
        
        For MikroTik captive portal, we might not need to manually add the user
        as the login process would happen through the redirect.
        
        This is here as a placeholder for potential additional functionality.
        """
        # Check if we're in development mode - if so, return success without contacting router
        if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true':
            logger.info(f"Development mode: Simulating successful user addition for: {username}")
            return True
            
        try:
            api = self.connect()
            
            # Check if the user already exists
            hotspot_users = api.get_resource('/ip/hotspot/user')
            existing_users = hotspot_users.get(name=username)
            
            # If user doesn't exist, create them
            if not existing_users:
                hotspot_users.add(
                    name=username,
                    password=password,
                    profile='default'
                )
                logger.debug(f"Created hotspot user: {username}")
            
            return True
        except Exception as e:
            logger.error(f"Error adding user: {str(e)}")
            return False
    
    def remove_user(self, user_id):
        """
        Disconnect a user from the hotspot and add to block list
        
        Args:
            user_id: This can be either the ID of the active connection or the username
        """
        # Check if we're in development mode - if so, return success without contacting router
        if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true':
            logger.info(f"Development mode: Simulating successful user removal for: {user_id}")
            return True
            
        try:
            api = self.connect()
            hotspot_active = api.get_resource('/ip/hotspot/active')
            
            # Store MAC address to block later if this is a username
            mac_to_block = None
            
            # Check if user_id is an active connection ID
            try:
                # If it's a connection ID, get the user details first to get the MAC
                user_details = hotspot_active.get(id=user_id)
                if user_details and len(user_details) > 0:
                    mac_to_block = user_details[0].get('mac-address')
                
                # Disconnect the user
                hotspot_active.remove(id=user_id)
                logger.debug(f"Disconnected user with connection ID: {user_id}")
                
                # Block the MAC address if found
                if mac_to_block:
                    self._block_mac_address(mac_to_block, user_details[0].get('user', 'unknown'))
                
                return True
            except Exception as e:
                logger.debug(f"Not a connection ID or error: {str(e)}")
                
                # If not, try to find the user by username
                active_users = hotspot_active.get(user=user_id)
                if active_users:
                    for user in active_users:
                        # Get MAC address before disconnecting
                        mac_to_block = user.get('mac-address')
                        
                        # Disconnect the user
                        hotspot_active.remove(id=user['id'])
                        logger.debug(f"Disconnected user: {user_id} with connection ID: {user['id']}")
                        
                        # Block the MAC address
                        if mac_to_block:
                            self._block_mac_address(mac_to_block, user_id)
                    
                    return True
                else:
                    logger.warning(f"User not found to disconnect: {user_id}")
                    return False
        except Exception as e:
            logger.error(f"Error removing user: {str(e)}")
            return False
    
    def _block_mac_address(self, mac_address, username):
        """
        Add a MAC address to the block list
        
        Args:
            mac_address: The MAC address to block
            username: The username (mobile number) for reference
        """
        if not mac_address:
            logger.warning("No MAC address provided to block")
            return False
            
        # Check if we're in development mode - if so, return success without contacting router
        if os.environ.get('DEVELOPMENT_MODE', 'false').lower() == 'true':
            logger.info(f"Development mode: Simulating MAC address blocking for: {mac_address} (user: {username})")
            return True
            
        # Check the MAC address format
        if not self._is_valid_mac(mac_address):
            logger.warning(f"Invalid MAC address format: {mac_address}")
            return False
                
        try:
            api = self.connect()
            
            # Add to MikroTik address list (for firewall)
            ip_firewall_addr_list = api.get_resource('/ip/firewall/address-list')
            
            # Check if already in the block list
            existing = ip_firewall_addr_list.get(address=mac_address, list="blocked-hotspot-users")
            if existing:
                logger.debug(f"MAC {mac_address} already in block list")
                return True
                
            # Add to the block list with a comment for reference
            ip_firewall_addr_list.add(
                list="blocked-hotspot-users",
                address=mac_address,
                comment=f"Blocked user: {username} on {time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            logger.info(f"Added MAC {mac_address} to block list (user: {username})")
            return True
            
        except Exception as e:
            logger.error(f"Error blocking MAC address: {str(e)}")
            return False
    
    def _is_valid_mac(self, mac):
        """
        Validate MAC address format
        
        Args:
            mac: The MAC address to validate
            
        Returns:
            Boolean indicating if MAC address is valid
        """
        import re
        # Basic MAC address format check
        pattern = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')
        return bool(pattern.match(mac))
