import os
import json
import time

COMMON_AUTOFILL_FIELDS = [
    {
        "key": "email",
        "labels": ["Email", "Email address", "Work email"],
        "placeholders": ["Email", "Email address", "Work email"],
        "selectors": ["input[type='email']", "input[name*='email' i]", "input[id*='email' i]"],
    },
    {
        "key": "username",
        "labels": ["Username", "User name", "Handle"],
        "placeholders": ["Username", "User name", "Handle"],
        "selectors": ["input[name*='user' i]", "input[id*='user' i]", "input[name*='handle' i]"],
    },
    {
        "key": "password",
        "labels": ["Password", "Create password"],
        "placeholders": ["Password", "Create password"],
        "selectors": ["input[type='password']", "input[name*='password' i]", "input[id*='password' i]"],
    },
    {
        "key": "business_name",
        "labels": ["Business name", "Company name", "Organization name", "Name"],
        "placeholders": ["Business name", "Company name", "Organization name"],
        "selectors": ["input[name*='business' i]", "input[name*='company' i]", "input[id*='business' i]", "input[id*='company' i]"],
    },
    {
        "key": "owner_name",
        "labels": ["Full name", "Name", "Owner name", "Contact name"],
        "placeholders": ["Full name", "Name", "Owner name", "Contact name"],
        "selectors": ["input[name*='full_name' i]", "input[name*='fullname' i]", "input[name*='owner' i]", "input[name*='contact' i]"],
    },
    {
        "key": "first_name",
        "labels": ["First name"],
        "placeholders": ["First name"],
        "selectors": ["input[name*='first' i]", "input[id*='first' i]"],
    },
    {
        "key": "last_name",
        "labels": ["Last name"],
        "placeholders": ["Last name"],
        "selectors": ["input[name*='last' i]", "input[id*='last' i]"],
    },
    {
        "key": "website",
        "labels": ["Website", "Website URL", "URL"],
        "placeholders": ["Website", "Website URL", "URL", "https://"],
        "selectors": ["input[type='url']", "input[name*='website' i]", "input[name*='url' i]", "input[id*='website' i]", "input[id*='url' i]"],
    },
    {
        "key": "phone",
        "labels": ["Phone", "Phone number", "Business phone"],
        "placeholders": ["Phone", "Phone number", "Business phone"],
        "selectors": ["input[type='tel']", "input[name*='phone' i]", "input[id*='phone' i]"],
    },
    {
        "key": "address",
        "labels": ["Address", "Street address", "Business address"],
        "placeholders": ["Address", "Street address", "Business address"],
        "selectors": ["input[name*='address' i]", "input[id*='address' i]"],
    },
    {
        "key": "city",
        "labels": ["City"],
        "placeholders": ["City"],
        "selectors": ["input[name*='city' i]", "input[id*='city' i]"],
    },
    {
        "key": "state",
        "labels": ["State", "Region"],
        "placeholders": ["State", "Region"],
        "selectors": ["input[name*='state' i]", "input[id*='state' i]", "input[name*='region' i]"],
    },
    {
        "key": "postal_code",
        "labels": ["Zip", "ZIP", "Postal code", "Postcode"],
        "placeholders": ["Zip", "ZIP", "Postal code", "Postcode"],
        "selectors": ["input[name*='zip' i]", "input[name*='postal' i]", "input[id*='zip' i]", "input[id*='postal' i]"],
    },
    {
        "key": "category",
        "labels": ["Category", "Business category", "Industry"],
        "placeholders": ["Category", "Business category", "Industry"],
        "selectors": ["input[name*='category' i]", "input[name*='industry' i]", "input[id*='category' i]", "input[id*='industry' i]"],
    },
    {
        "key": "description",
        "labels": ["Description", "Business description", "About", "Bio"],
        "placeholders": ["Description", "Business description", "About", "Bio"],
        "selectors": ["textarea[name*='description' i]", "textarea[name*='about' i]", "textarea[name*='bio' i]", "textarea[id*='description' i]", "textarea[id*='about' i]", "textarea[id*='bio' i]"],
    },
]

class BaseSite:
    def __init__(self, engine, captcha_solver, config_path=None, config_data=None):
        self.engine = engine
        self.captcha_solver = captcha_solver
        self.config_data = {}
        if config_data:
            self.config_data = config_data
        if config_path:
            self.load_config(config_path)
        self.workflow_context = {}
        self.result_details = {}
        self.last_autofill_count = 0

    def load_config(self, config_path):
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                self.config_data = json.load(f)

    def build_context(self, email, username, password, extra_context=None):
        context = {
            "email": email,
            "username": username,
            "password": password,
        }
        if self.config_data:
            context.update({
                "site_slug": self.config_data.get("slug", ""),
                "site_name": self.config_data.get("name", ""),
                "signup_url": self.config_data.get("signup_url", ""),
                "website_url": self.config_data.get("website_url", ""),
            })
        if extra_context:
            context.update(extra_context)
        return context

    def format_value(self, value):
        if isinstance(value, str):
            return value.format_map(DefaultFormatDict(self.workflow_context))
        return value

    def run(self, email, username, password, extra_context=None):
        """
        Executes the account creation workflow.
        Can run fully dynamically from config JSON or be overridden by subclass.
        """
        try:
            self.workflow_context = self.build_context(email, username, password, extra_context)
            self.last_autofill_count = 0
            self.pre_run(email, username, password)

            self.execute_steps(self.config_data.get("steps", []), email, username, password)

            return self.post_run(email, username, password)

        except Exception as e:
            print(f"Workflow error: {e}")
            return False

    def pre_run(self, email, username, password):
        """Hook executed before signup starts."""
        pass

    def post_run(self, email, username, password):
        """Hook executed after signup finishes. Return True if account successfully created."""
        return True

    def execute_steps(self, steps, email=None, username=None, password=None, skip_pause=False):
        for step in steps:
            action = step.get("action")
            selector = step.get("selector")
            value = self.format_value(step.get("value", ""))

            print(f"Executing action: {action} on {selector or 'N/A'}")

            if action == "navigate":
                url = self.format_value(step.get("url"))
                self.engine.goto(url)
            elif action == "fill":
                self.engine.wait_for_selector(selector)
                self.engine.fill_humanlike(selector, value)
            elif action == "click":
                self.engine.wait_for_selector(selector)
                self.engine.click(selector)
            elif action == "select":
                self.engine.wait_for_selector(selector)
                self.select_option(selector, value)
            elif action == "wait":
                self.engine.wait_for_selector(selector, timeout_ms=step.get("timeout_ms"))
            elif action == "sleep":
                time.sleep(step.get("seconds", 2))
            elif action == "autofill_common":
                self.autofill_common(step.get("fields"))
            elif action == "pause":
                if skip_pause:
                    continue
                message = self.format_value(step.get("message", "Complete the visible step in the browser, then press Enter."))
                print(message)
                self.engine.solve_manually()
            elif action == "print":
                print(value)
            elif action == "custom":
                method_name = step.get("method")
                if hasattr(self, method_name):
                    getattr(self, method_name)(email, username, password)
                else:
                    print(f"Warning: Custom method {method_name} not implemented.")

    def select_option(self, selector, value):
        page = self.engine.page
        try:
            page.select_option(selector, label=str(value))
        except Exception:
            page.select_option(selector, value=str(value))

    def autofill_common(self, fields=None):
        page = self.engine.page
        if not page:
            print("Autofill skipped: browser page is not available.")
            return 0

        field_specs = fields or COMMON_AUTOFILL_FIELDS
        filled_count = 0
        for field in field_specs:
            key = field.get("key")
            raw_value = self.workflow_context.get(key, "")
            value = self.format_value(raw_value)
            if value in ("", None):
                continue
            if self.fill_field_candidates(field, value):
                filled_count += 1

        print(f"Autofill complete. Filled {filled_count} field(s) where matching inputs were found.")
        self.last_autofill_count += filled_count
        return filled_count

    def fill_field_candidates(self, field, value):
        selectors = field.get("selectors", [])
        labels = field.get("labels", [])
        placeholders = field.get("placeholders", [])

        for selector in selectors:
            if self.try_fill_locator_candidates(lambda selector=selector: self.engine.page.locator(selector), value):
                return True
        for label in labels:
            if self.try_fill_locator_candidates(lambda label=label: self.engine.page.get_by_label(label, exact=False), value):
                return True
        for placeholder in placeholders:
            if self.try_fill_locator_candidates(lambda placeholder=placeholder: self.engine.page.get_by_placeholder(placeholder, exact=False), value):
                return True

        return False

    def try_fill_locator_candidates(self, locator_factory, value):
        try:
            locator = locator_factory()
            count = min(locator.count(), 10)
        except Exception:
            return False

        for index in range(count):
            if self.try_fill_locator(lambda index=index: locator.nth(index), value):
                return True
        return False

    def try_fill_locator(self, locator_factory, value):
        try:
            locator = locator_factory()
            if locator.count() < 1:
                return False
            is_visible = locator.is_visible(timeout=750)
            dom_visible = locator.evaluate("el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)")
            if not is_visible and not dom_visible:
                return False
            if not locator.is_enabled(timeout=750):
                return False

            tag_name = locator.evaluate("el => el.tagName.toLowerCase()")
            input_type = locator.evaluate("el => (el.getAttribute('type') || '').toLowerCase()")
            if tag_name not in {"input", "textarea"} or input_type in {"hidden", "submit", "button", "checkbox", "radio", "file"}:
                return False
            if locator.evaluate("el => el.disabled || el.readOnly"):
                return False

            current_value = locator.input_value(timeout=750)
            if current_value and current_value not in {"http://", "https://"}:
                return False

            if is_visible:
                locator.fill(str(value), timeout=2000)
            else:
                locator.evaluate(
                    """(el, value) => {
                        el.focus();
                        el.value = value;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    str(value)
                )
            return True
        except Exception:
            return False

class DefaultFormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"
