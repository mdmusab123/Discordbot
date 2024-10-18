import json
import socks
import socket
import time

# Path to ip_status.json
IP_STATUS_FILE = 'ip_status.json'

# Proxy credentials (these won't be saved to the JSON file)
proxy_credentials = {
    "49.0.41.6": {"port": 14852, "username": "REXFTP", "password": "REXFTP86325"},
    "103.35.109.22": {"port": 4040, "username": "REXFTP", "password": "REXFTP563258"},  # wrong password for testing
    "103.35.109.205": {"port": 1088, "username": "REXFTP", "password": "REXFTP158635"},
    "111.221.5.150": {"port": 1088, "username": "REXFTP", "password": "pass1"},
    "202.4.123.74": {"port": 1088, "username": "REXFTP", "password": "REXFTP125846"},  # wrong password for testing
    "203.83.184.17": {"port": 12546, "username": "REXFTP", "password": "REXFTP56324"},
    "103.171.143.137": {"port": 9087, "username": "test", "password": "test"},
}

# Function to check if a SOCKS5 proxy with username/password is active using PySocks
def check_socks5_proxy(ip, port, username, password, timeout=5):
    try:
        # Create a SOCKS5 proxy connection using PySocks
        socks.set_default_proxy(socks.SOCKS5, ip, port, username=username, password=password)
        socket.socket = socks.socksocket

        # Test connection by trying to resolve a domain (example.com)
        sock = socket.create_connection(("example.com", 80), timeout)
        sock.close()

        return True  # If connection is successful, proxy is active
    except Exception as e:
        print(f"Proxy check failed for {ip}: {e}")
        return False  # If connection or authentication fails, proxy is inactive

# Function to update the status of IPs in ip_status.json
def update_ip_status(ip_status):
    # Open and write to ip_status.json
    with open(IP_STATUS_FILE, 'w') as file:
        json.dump(ip_status, file, indent=4)

# Function to check all proxies and update status
def check_proxies():
    # Load the current IP status from ip_status.json
    with open(IP_STATUS_FILE, 'r') as file:
        ip_status = json.load(file)

    # Loop through each IP and credentials in the proxy_credentials dictionary
    for ip, credentials in proxy_credentials.items():
        port = credentials["port"]
        username = credentials["username"]
        password = credentials["password"]

        # Check the proxy status using authentication
        if check_socks5_proxy(ip, port, username, password):
            print(f"{ip} is active")
            ip_status[ip] = "active"
        else:
            print(f"{ip} is inactive")
            ip_status[ip] = "inactive"

    # Update the ip_status.json file with the new statuses
    update_ip_status(ip_status)

# Main function to run the checker every 5 minutes (300 seconds)
def main():
    while True:
        print("Checking IP statuses...")
        check_proxies()
        time.sleep(300)  # Sleep for 5 minutes before checking again

if __name__ == '__main__':
    main()
