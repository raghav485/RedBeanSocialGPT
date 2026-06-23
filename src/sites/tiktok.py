import time
import random
from .base_site import BaseSite

class TikTokSite(BaseSite):
    def __init__(self, engine, captcha_solver, temp_mail_client=None):
        super().__init__(engine, captcha_solver, "config/tiktok.json")
        self.temp_mail = temp_mail_client

    def handle_tiktok_flow(self, email, username, password):
        page = self.engine.page
        print("Handling TikTok registration flow...")

        try:
            # 1. Click "Use phone or email" if option list is visible
            try:
                page.wait_for_selector('p:has-text("Use phone or email")', timeout=10000)
                page.click('p:has-text("Use phone or email")')
                time.sleep(2)
            except Exception:
                pass # Already on page or layout differs

            # 2. Make sure email tab is selected
            try:
                page.wait_for_selector('a:has-text("Sign up with email")', timeout=5000)
                page.click('a:has-text("Sign up with email")')
                time.sleep(1)
            except Exception:
                # Alternatively check for link containing "email"
                if page.locator('a[href*="email"]').count() > 0:
                    page.locator('a[href*="email"]').first.click()

            # 3. Enter Birthday
            print("Selecting birthday...")
            # Try finding select drop downs (month, day, year)
            if page.locator('select').count() >= 3:
                page.select_option('select:nth-of-type(1)', index=2) # Feb
                time.sleep(0.5)
                page.select_option('select:nth-of-type(2)', index=10) # 10
                time.sleep(0.5)
                page.select_option('select:nth-of-type(3)', label="1996") # 1996
            else:
                # Custom TikTok dropdowns
                page.click('div[placeholder="Month"]')
                time.sleep(0.5)
                page.click('li:has-text("January")')
                
                page.click('div[placeholder="Day"]')
                time.sleep(0.5)
                page.click('li:has-text("15")')
                
                page.click('div[placeholder="Year"]')
                time.sleep(0.5)
                page.click('li:has-text("1995")')

            # 4. Fill Email and Password
            page.wait_for_selector('input[type="email"]', timeout=10000)
            self.engine.fill_humanlike('input[type="email"]', email)
            time.sleep(random.uniform(0.5, 1.0))
            self.engine.fill_humanlike('input[type="password"]', password)
            time.sleep(random.uniform(1.0, 2.0))

            # 5. Click "Send code"
            send_code_btn = page.locator('button:has-text("Send code")').first
            send_code_btn.click()
            print("Send code clicked.")
            time.sleep(3)

            # 6. Check for TikTok Slider CAPTCHA
            # TikTok CAPTCHAs are highly advanced sliding canvases and cannot be easily bypassed with typical tools.
            # We pause here for the user to solve it manually.
            print("Checking for TikTok security verification / puzzle slider...")
            time.sleep(5)
            # Since TikTok sliders display in a canvas container or iframe
            self.captcha_solver.solve_manually()

            # 7. Wait for verification code entry field
            page.wait_for_selector('input[placeholder="Enter 6-digit code"]', timeout=15000)
            
            otp_code = None
            if self.temp_mail and email == self.temp_mail.email_address:
                print("Polling 1secmail API for TikTok confirmation code...")
                otp_code = self.temp_mail.poll_for_code(timeout_sec=90, sender_keyword="tiktok")

            if not otp_code:
                print("\n" + "="*50)
                print(f"Please check email {email} for a TikTok verification code.")
                if self.engine.headless:
                    otp_code = input("Enter 6-digit TikTok verification code: ").strip()
                else:
                    otp_code = input("Enter 6-digit code here (or press Enter if entered directly in browser): ").strip()

            if otp_code:
                self.engine.fill_humanlike('input[placeholder="Enter 6-digit code"]', otp_code)
                time.sleep(2)
                
            # Submit / Next
            page.keyboard.press("Enter")
            print("Submitted verification code.")
            time.sleep(5)

        except Exception as e:
            print(f"TikTok signup process failed: {e}")

    def post_run(self, email, username, password):
        page = self.engine.page
        time.sleep(5)
        # Check if URL redirected to TikTok dashboard or main page
        if "signup" not in page.url and "tiktok.com" in page.url:
            print(f"TikTok signup success for {username}!")
            return True
        else:
            print("TikTok signup did not redirect. Current URL: " + page.url)
            return False
