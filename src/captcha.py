from capmonster_python import CapmonsterClient, RecaptchaV2Task
import time

class CaptchaRequiredException(Exception):
    pass

class CaptchaSolver:
    def __init__(self, capmonster_key=None, on_captcha_callback=None):
        self.capmonster_key = capmonster_key
        self.on_captcha_callback = on_captcha_callback
        
    def solve_recaptcha_v2(self, site_url, site_key):
        """
        Tries to solve reCAPTCHA v2 using CapMonster if API key is available.
        """
        if not self.capmonster_key:
            print("No CapMonster API key provided. Falling back to manual resolution.")
            return self.solve_manually()

        try:
            print("Attempting to solve reCAPTCHA v2 automatically via CapMonster...")
            client = CapmonsterClient(api_key=self.capmonster_key)
            task = RecaptchaV2Task(websiteURL=site_url, websiteKey=site_key)
            result = client.solve(task)
            return result.get("gRecaptchaResponse")
        except Exception as e:
            print(f"CapMonster auto-solve failed: {e}. Falling back to manual resolution.")
            return self.solve_manually()

    def solve_manually(self):
        """
        Pauses and waits for manual captcha resolution.
        """
        print("\n" + "="*50)
        print(" [CAPTCHA DETECTED] ")
        print("Please solve the captcha inside the open browser window.")
        print("="*50 + "\n")

        if self.on_captcha_callback:
            # Call GUI callback (which can open a popup dialog)
            self.on_captcha_callback()
        else:
            # Command Line interface fallback
            input("After solving the CAPTCHA, press [ENTER] here to continue...")
        
        return True
