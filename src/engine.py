import time
import random
from playwright.sync_api import sync_playwright

class PlaywrightEngine:
    def __init__(self, headless=False, proxy=None, user_agent=None, timeout_ms=30000):
        self.headless = headless
        self.proxy = proxy
        self.user_agent = user_agent
        self.timeout_ms = timeout_ms
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def start(self):
        self.playwright = sync_playwright().start()
        
        # Configure proxy for Playwright if available
        # Playwright proxy format: {'server': 'http://host:port', 'username': '...', 'password': '...'}
        launch_args = []
        
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args
        )

        # Setup context with spoofed headers / stealth settings
        context_kwargs = {
            "viewport": {"width": 1280, "height": 800},
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False,
            "locale": "en-US",
            "timezone_id": "America/New_York",
        }

        if self.proxy:
            context_kwargs["proxy"] = self.proxy

        if self.user_agent:
            context_kwargs["user_agent"] = self.user_agent

        self.context = self.browser.new_context(**context_kwargs)
        self.context.set_default_timeout(self.timeout_ms)
        
        # Add basic anti-webdriver detection scripts
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
        """)

        self.page = self.context.new_page()
        return self.page

    def goto(self, url):
        if self.page:
            self.page.goto(url, wait_until="domcontentloaded")

    def fill_humanlike(self, selector, text):
        if not self.page:
            return
        
        self.page.focus(selector)
        # Clear field first
        self.page.keyboard.press("Meta+A")
        self.page.keyboard.press("Backspace")
        
        for char in text:
            self.page.keyboard.type(char)
            # Human-like delay between keystrokes
            time.sleep(random.uniform(0.05, 0.15))

    def click(self, selector):
        if self.page:
            # Click with a small delay before and after to mimic human movement
            time.sleep(random.uniform(0.2, 0.5))
            self.page.click(selector)
            time.sleep(random.uniform(0.2, 0.5))

    def wait_for_selector(self, selector, timeout_ms=None):
        if self.page:
            t = timeout_ms if timeout_ms is not None else self.timeout_ms
            return self.page.wait_for_selector(selector, timeout=t)
        return None

    def is_visible(self, selector):
        if self.page:
            try:
                return self.page.is_visible(selector)
            except Exception:
                return False
        return False

    def solve_manually(self, on_solve_callback=None):
        """
        Pauses execution to allow manual browser solving of captchas/OTP.
        """
        print("\n[PAUSE] Waiting for user action in the browser...")
        if on_solve_callback:
            on_solve_callback()
        else:
            input("Solve the challenge in the browser window, then press [ENTER] here to continue...")

    def stop(self):
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception:
            pass
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
