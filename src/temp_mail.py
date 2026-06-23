import requests
import random
import string
import time
import re

class TempMail:
    def __init__(self):
        self.domains = ["1secmail.com", "1secmail.org", "1secmail.net"]
        self.login = ""
        self.domain = ""
        self.email_address = ""
        self.fetch_domains()

    def fetch_domains(self):
        try:
            r = requests.get("https://www.1secmail.com/api/v1/?action=getDomainList")
            if r.status_code == 200:
                self.domains = r.json()
        except Exception:
            pass  # Fallback to hardcoded domains

    def generate_email(self):
        # Generate random 10-character string
        self.login = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        self.domain = random.choice(self.domains)
        self.email_address = f"{self.login}@{self.domain}"
        return self.email_address

    def get_messages(self):
        if not self.login or not self.domain:
            return []
        url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={self.login}&domain={self.domain}"
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return []

    def read_message(self, message_id):
        url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={self.login}&domain={self.domain}&id={message_id}"
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def poll_for_code(self, timeout_sec=120, poll_interval=5, sender_keyword=None):
        """
        Polls the inbox for a verification code.
        Looks in subjects and message bodies.
        Returns the first sequence of 4-8 digits found, or a verification link.
        """
        print(f"Polling inbox for {self.email_address}...")
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            messages = self.get_messages()
            for msg in messages:
                # Optional check for sender
                if sender_keyword:
                    sender = msg.get("from", "").lower()
                    subject = msg.get("subject", "").lower()
                    if sender_keyword.lower() not in sender and sender_keyword.lower() not in subject:
                        continue

                # Get full message content
                details = self.read_message(msg["id"])
                if details:
                    body = details.get("textBody", "") + details.get("htmlBody", "") + details.get("subject", "")
                    
                    # Try finding standard 4 to 8 digit OTP code
                    code_match = re.search(r'\b(\d{4,8})\b', body)
                    if code_match:
                        print(f"Found code: {code_match.group(1)}")
                        return code_match.group(1)

                    # Try finding a verification link (if no numerical code is obvious)
                    link_match = re.search(r'https?://[^\s"\'<>]+confirm[^\s"\'<>]*', body, re.IGNORECASE)
                    if link_match:
                        print(f"Found confirmation link: {link_match.group(0)}")
                        return link_match.group(0)

            time.sleep(poll_interval)
        print("Polling timeout reached: No verification message received.")
        return None
