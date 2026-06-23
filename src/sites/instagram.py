import time
import random
from .base_site import BaseSite

class InstagramSite(BaseSite):
    def __init__(self, engine, captcha_solver, temp_mail_client=None):
        super().__init__(engine, captcha_solver, "config/instagram.json")
        self.temp_mail = temp_mail_client

    def handle_birthday_and_otp(self, email, username, password):
        page = self.engine.page
        
        # 1. Handle Birthday selection
        print("Handling Instagram birthday page...")
        try:
            # Wait for Month selector
            page.wait_for_selector('select[title="Month:"]', timeout=10000)
            
            # Select values (e.g., January 15, 1995 to be >18 years old)
            page.select_option('select[title="Month:"]', index=1)  # January
            time.sleep(random.uniform(0.5, 1.0))
            page.select_option('select[title="Day:"]', index=15)   # 15
            time.sleep(random.uniform(0.5, 1.0))
            page.select_option('select[title="Year:"]', label="1995")  # 1995
            time.sleep(random.uniform(0.5, 1.0))

            # Click Next
            next_button = page.locator('button:has-text("Next")').first
            next_button.click()
            print("Birthday submitted successfully.")
        except Exception as e:
            print(f"Birthday selection failed (might have been skipped): {e}")

        # 2. Handle CAPTCHA if it appears here
        time.sleep(3)
        if self.engine.is_visible("iframe[title*='reCAPTCHA']"):
            print("ReCAPTCHA challenge detected on Instagram.")
            self.captcha_solver.solve_manually()

        # 3. Handle Email OTP Verification
        print("Waiting for Instagram verification code input field...")
        try:
            page.wait_for_selector('input[name="email_confirmation_code"]', timeout=15000)
            print("Verification code field visible.")
            
            otp_code = None
            if self.temp_mail and email == self.temp_mail.email_address:
                # Dynamic polling if we created this email
                print("Polling 1secmail API for verification code...")
                otp_code = self.temp_mail.poll_for_code(timeout_sec=90, sender_keyword="instagram")

            if not otp_code:
                # Manual entry fallback
                print("\n" + "="*50)
                print(f"Please check the email {email} for an Instagram code.")
                if self.engine.headless:
                    # CLI input
                    otp_code = input("Enter the 6-digit confirmation code: ").strip()
                else:
                    # If headful, user can type directly in browser or terminal
                    print("You can type the code directly into the browser window or terminal.")
                    otp_code = input("Enter the 6-digit code here (or press Enter if typed in browser): ").strip()
            
            if otp_code:
                self.engine.fill_humanlike('input[name="email_confirmation_code"]', otp_code)
                time.sleep(random.uniform(1.0, 2.0))
                # Submit
                page.keyboard.press("Enter")
                print("Verification code submitted.")
                time.sleep(5)
        except Exception as e:
            print(f"Verification screen not loaded or failed: {e}")

    def post_run(self, email, username, password):
        page = self.engine.page
        time.sleep(5)
        # Check if we logged in or navigated away from registration page
        if "emailsignup" not in page.url and "instagram.com" in page.url:
            print(f"Instagram signup success for {username}!")
            return True
        else:
            # Check for generic block/error screens
            print("Instagram signup page did not redirect. Likely blocked or requires manual verification.")
            return False
