import logging
import routeros_api
from config import MIKROTIK_HOST, MIKROTIK_PORT, MIKROTIK_USERNAME, MIKROTIK_PASSWORD

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
            except Exception as e:
                logger.error(f"Failed to connect to MikroTik router: {str(e)}")
                self.connection = None
                raise e
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
        except Exception as e:
            logger.error(f"Error getting active users: {str(e)}")
            raise e
    
    def add_user(self, username, password):
        """
        Add a user to the hotspot users (if needed) and authenticate them
        
        For MikroTik captive portal, we might not need to manually add the user
        as the login process would happen through the redirect.
        
        This is here as a placeholder for potential additional functionality.
        """
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
        Disconnect a user from the hotspot
        
        Args:
            user_id: This can be either the ID of the active connection or the username
        """
        try:
            api = self.connect()
            hotspot_active = api.get_resource('/ip/hotspot/active')
            
            # Check if user_id is an active connection ID
            try:
                hotspot_active.remove(id=user_id)
                logger.debug(f"Disconnected user with connection ID: {user_id}")
                return True
            except Exception:
                # If not, try to find the user by username
                active_users = hotspot_active.get(user=user_id)
                if active_users:
                    for user in active_users:
                        hotspot_active.remove(id=user['id'])
                        logger.debug(f"Disconnected user: {user_id} with connection ID: {user['id']}")
                    return True
                else:
                    logger.warning(f"User not found to disconnect: {user_id}")
                    return False
        except Exception as e:
            logger.error(f"Error removing user: {str(e)}")
            return False
