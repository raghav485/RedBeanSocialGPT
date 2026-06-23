from .base_site import BaseSite


class GenericSite(BaseSite):
    def __init__(self, engine, captcha_solver, temp_mail_client=None, config_path=None, config_data=None):
        super().__init__(engine, captcha_solver, config_path=config_path, config_data=config_data)
        self.temp_mail = temp_mail_client
        if self.config_data and not self.config_data.get("steps"):
            self.config_data["steps"] = [
                {"action": "navigate", "url": "{signup_url}"},
                {"action": "sleep", "seconds": 2},
                {"action": "autofill_common"},
                {
                    "action": "print",
                    "value": "Opened {site_name} and attempted to autofill common account/listing fields with your approved details."
                },
                {
                    "action": "pause",
                    "message": "Review the filled fields, complete any missing fields and allowed verification in the browser, then press Enter here."
                }
            ]

    def post_run(self, email, username, password):
        success_mode = self.config_data.get("success_mode", "manual")
        if success_mode == "always":
            return True

        answer = input("Mark this website as completed? [y/N]: ").strip().lower()
        is_complete = answer in {"y", "yes"}
        if is_complete:
            profile_url = input("Profile/listing URL, if available: ").strip()
            notes = input("Notes, if any: ").strip()
            self.result_details = {
                "profile_url": profile_url,
                "notes": notes,
            }
        return is_complete
