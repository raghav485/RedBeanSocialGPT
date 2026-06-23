import time
import random
from .base_site import BaseSite

class RedditSite(BaseSite):
    def __init__(self, engine, captcha_solver, temp_mail_client=None):
        super().__init__(engine, captcha_solver, "config/reddit.json")
        self.temp_mail = temp_mail_client

    def handle_username_password(self, email, username, password):
        page = self.engine.page
        print("Handling Reddit second signup screen (username & password)...")
        
        try:
            # Wait for username and password fields to load
            page.wait_for_selector('input[name="user"]', timeout=15000)
            
            # Fill credentials
            self.engine.fill_humanlike('input[name="user"]', username)
            time.sleep(random.uniform(0.5, 1.0))
            self.engine.fill_humanlike('input[name="passwd"]', password)
            time.sleep(random.uniform(0.5, 1.0))

            # Look for CAPTCHA
            time.sleep(2)
            if self.engine.is_visible("iframe[title*='reCAPTCHA']") or self.engine.is_visible(".g-recaptcha"):
                print("ReCAPTCHA detected on Reddit!")
                self.captcha_solver.solve_manually()

            # Submit
            submit_btn = page.locator('button.create').first
            submit_btn.click()
            print("Reddit signup submitted.")
            time.sleep(5)
        except Exception as e:
            print(f"Reddit second-page signup failed: {e}")

    def post_run(self, email, username, password):
        page = self.engine.page
        time.sleep(5)
        # If redirected to main dashboard or verification screens
        if "register" not in page.url and "reddit.com" in page.url:
            print(f"Reddit signup success for {username}!")
            return True
        else:
            print("Reddit signup did not complete. Page URL: " + page.url)
            return False
