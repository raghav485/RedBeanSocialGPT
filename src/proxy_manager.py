import random
import os
import requests

class ProxyManager:
    def __init__(self, file_path='proxy.txt'):
        self.file_path = file_path
        self.proxies = []
        self.load_proxies()

    def load_proxies(self):
        if not os.path.exists(self.file_path):
            # Create an empty proxy file if it doesn't exist
            with open(self.file_path, 'w') as f:
                pass
            return

        with open(self.file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    parsed = self.parse_proxy_string(line)
                    if parsed:
                        self.proxies.append(parsed)

    def parse_proxy_string(self, proxy_str):
        """
        Parses proxy strings of various formats:
        - http://user:pass@host:port
        - host:port:user:pass
        - host:port
        Returns a dict suitable for Playwright:
        {
            'server': 'http://host:port',
            'username': 'user',  # optional
            'password': 'pass'   # optional
        }
        """
        if not proxy_str:
            return None

        # Clean scheme prefix if any
        scheme = "http"
        if "://" in proxy_str:
            scheme, proxy_str = proxy_str.split("://", 1)

        # Format: user:pass@host:port
        if "@" in proxy_str:
            auth, host_port = proxy_str.split("@", 1)
            user = ""
            password = ""
            if ":" in auth:
                user, password = auth.split(":", 1)
            else:
                user = auth
            return {
                "server": f"{scheme}://{host_port}",
                "username": user,
                "password": password
            }

        # Format: host:port:user:pass
        parts = proxy_str.split(":")
        if len(parts) == 4:
            host, port, user, password = parts
            return {
                "server": f"{scheme}://{host}:{port}",
                "username": user,
                "password": password
            }
        # Format: host:port
        elif len(parts) == 2:
            host, port = parts
            return {
                "server": f"{scheme}://{host}:{port}"
            }
        
        return None

    def get_random_proxy(self):
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    def validate_proxy(self, proxy_dict, timeout=5):
        """
        Checks if the proxy works by calling httpbin.org.
        """
        if not proxy_dict:
            return False

        server = proxy_dict['server']
        proxies_arg = {
            "http": server,
            "https": server
        }
        
        auth = None
        if 'username' in proxy_dict and 'password' in proxy_dict:
            auth = (proxy_dict['username'], proxy_dict['password'])

        try:
            # We use a simple HTTP GET request to check connectivity
            response = requests.get(
                "https://httpbin.org/ip", 
                proxies=proxies_arg, 
                auth=auth, 
                timeout=timeout
            )
            return response.status_code == 200
        except Exception:
            return False
