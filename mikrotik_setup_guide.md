# MikroTik RB941 2nd Haplite Router Configuration Guide
## For External Captive Portal Authentication System

### PART 1: ACCESSING YOUR ROUTER

1. **Connect to your router**:
   - Connect your computer to the router using an Ethernet cable
   - Plug the cable into any LAN port (usually ports 2-4)

2. **Access the router administration**:
   - Open a web browser (Chrome, Firefox, etc.)
   - Type `192.168.88.1` in the address bar (default IP)
   - Press Enter

3. **Login to your router**:
   - Username: admin (default)
   - Password: (blank by default or your custom password)
   - Click the blue "Login" button

### PART 2: ENABLE API ACCESS

1. **Navigate to IP Services**:
   - In the left menu, click on "IP"
   - From the dropdown, click on "Services"

2. **Enable the API service**:
   - In the services list, look for "api" (usually enabled by default)
   - If it's not enabled, double-click on "api" to open its settings
   - Make sure "Enabled" is checked
   - Set "Available From" to either your specific server IP or 0.0.0.0/0 (all addresses, less secure)
   - Click "OK" to save

3. **Create a dedicated API user (recommended)**:
   - In the left menu, click on "System"
   - Click on "Users"
   - Click the blue "+" button to add a new user
   - Enter a username (e.g., "apiuser")
   - Enter a strong password
   - Set Group to "full" (or create a custom group with more limited permissions)
   - Click "OK" to save

### PART 3: CONFIGURE HOTSPOT

1. **Setup the Hotspot Interface**:
   - In the left menu, click on "IP"
   - Click on "Hotspot"
   - Click on the blue "Hotspot Setup" button
   - Select your public interface (usually "ether1" or "wlan1")
   - Click "Next"

2. **Configure Local Address**:
   - Keep the default local address (usually 192.168.88.1) or change if needed
   - Click "Next"

3. **Set Address Pool**:
   - Keep the default address pool (usually 192.168.88.10-192.168.88.254) or change if needed
   - Click "Next"

4. **Select Certificate**:
   - Select "none" for certificate (we'll use our external authentication)
   - Click "Next"

5. **SMTP Server**:
   - Leave blank, click "Next"

6. **DNS Servers**:
   - Keep default values (usually 192.168.88.1 or your custom DNS)
   - Click "Next"

7. **DNS Name**:
   - Type a domain name for local identification (e.g., "hotel.hotspot")
   - Click "Next"

8. **Complete Setup**:
   - Review the setup and click "Next"
   - Click "OK" on the final confirmation

### PART 4: CONFIGURE EXTERNAL LOGIN PAGE

1. **Modify Hotspot Settings**:
   - In the left menu, click on "IP"
   - Click on "Hotspot"
   - Click on the "Server Profiles" tab
   - Double-click on the default profile ("hsprof1")

2. **Change Login Page**:
   - Find "Login By" dropdown and select "HTTP PAP"
   - Find "Login Page" field
   - Replace with the URL of your deployed application (e.g., https://your-app-name.replit.app)
   - Click "OK" to save

### PART 5: CONFIGURE FIREWALL FOR API ACCESS

1. **Add a Firewall Rule**:
   - In the left menu, click on "IP"
   - Click on "Firewall"
   - Click on the "Filter Rules" tab
   - Click the blue "+" button to add a new rule

2. **Configure the Rule**:
   - In the "General" tab:
     - Set "Chain" to "input"
     - Set "Protocol" to "tcp"
     - Set "Dst. Port" to "8728" (API port)
   - In the "Action" tab:
     - Set "Action" to "accept"
   - Click "OK" to save

### PART 6: UPDATE APPLICATION SETTINGS

1. **Note your router's public IP**:
   - If your router has a static public IP, note it down
   - If you're using a dynamic IP, consider using a Dynamic DNS service

2. **Update the application environment variables**:
   - MIKROTIK_HOST: Your router's public IP or domain
   - MIKROTIK_USERNAME: The admin or API user you created
   - MIKROTIK_PASSWORD: The password for that user

3. **Testing the connection**:
   - Make sure your application server can reach your router's API port (8728)
   - Verify that the router allows incoming connections from your server's IP

### PART 7: CREATE BLOCK LIST FOR DISCONNECTED USERS

1. **Create Address List**:
   - In the left menu, click on "IP"
   - Click on "Firewall"
   - Click on the "Address Lists" tab
   - Click the blue "+" button to add a new address list

2. **Configure Address List**:
   - Set "List Name" to "blocked-hotspot-users"
   - Click "OK" to save

3. **Create Blocking Rule**:
   - In the "Filter Rules" tab, click the blue "+" button
   - In the "General" tab:
     - Set "Chain" to "forward"
     - Set "Src. Address List" to "blocked-hotspot-users"
   - In the "Action" tab:
     - Set "Action" to "drop"
   - In the "Advanced" tab:
     - Set "Comment" to "Block disconnected hotspot users"
   - Click "OK" to save
   - Use the up arrows to move this rule above the hotspot rules

## Troubleshooting

If you encounter issues with the connection between your application and the MikroTik router:

1. **Check API accessibility**:
   - Verify the API service is enabled and running
   - Ensure the firewall allows connections to port 8728 from your server's IP
   - Try accessing the API from the same network to isolate network issues

2. **Verify credentials**:
   - Double-check username and password
   - Ensure the user has sufficient permissions

3. **Network connectivity**:
   - If your router is behind NAT, ensure port forwarding is set up for the API port
   - Check if any firewall between the server and router might be blocking connections

## Support

For additional help or questions:
- MikroTik documentation: https://help.mikrotik.com/docs/
- RouterOS API documentation: https://wiki.mikrotik.com/wiki/Manual:API