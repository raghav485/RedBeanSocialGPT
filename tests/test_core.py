import unittest
from tempfile import TemporaryDirectory

import main
from src.proxy_manager import ProxyManager
from src.sites import get_available_site_names, get_site_definitions
from src.submission_tracker import append_submission
from src.sites.generic import GenericSite


class FakeEngine:
    page = None


class CoreTests(unittest.TestCase):
    def test_load_settings_has_required_defaults(self):
        settings = main.load_settings()

        self.assertIn("headless", settings)
        self.assertIn("default_timeout_ms", settings)
        self.assertIn("output_csv", settings)
        self.assertIn("user_agent", settings)

    def test_generated_credentials_are_non_empty(self):
        username = main.generate_random_username()
        password = main.generate_random_password()

        self.assertGreaterEqual(len(username), 11)
        self.assertGreaterEqual(len(password), 12)

    def test_proxy_formats(self):
        with TemporaryDirectory() as tmpdir:
            manager = ProxyManager(file_path=f"{tmpdir}/missing-test-proxy-file.txt")

            self.assertEqual(
                manager.parse_proxy_string("host.example:8080"),
                {"server": "http://host.example:8080"},
            )
            self.assertEqual(
                manager.parse_proxy_string("host.example:8080:user:pass"),
                {
                    "server": "http://host.example:8080",
                    "username": "user",
                    "password": "pass",
                },
            )
            self.assertEqual(
                manager.parse_proxy_string("https://user:pass@host.example:8080"),
                {
                    "server": "https://host.example:8080",
                    "username": "user",
                    "password": "pass",
                },
            )

    def test_backlink_sites_are_registered(self):
        site_names = get_available_site_names()
        definitions = get_site_definitions()

        self.assertIn("about-me", site_names)
        self.assertIn("github", site_names)
        self.assertIn("detailerdirectory", site_names)
        self.assertEqual(definitions["about-me"]["runner"], "json")

    def test_resolve_selected_sites(self):
        available_sites = ["about-me", "github", "detailerdirectory"]

        self.assertEqual(
            main.resolve_selected_sites(None, "about-me,github,about-me", available_sites),
            ["about-me", "github"],
        )
        self.assertEqual(
            main.resolve_selected_sites(None, "all", available_sites),
            available_sites,
        )
        self.assertEqual(
            main.resolve_selected_sites("github", None, available_sites),
            ["github"],
        )

    def test_submission_tracker_writes_csv(self):
        with TemporaryDirectory() as tmpdir:
            path = f"{tmpdir}/submissions.csv"
            append_submission(
                path,
                site="about-me",
                site_name="about.me",
                status="completed",
                email="person@example.com",
                username="person",
                profile_url="https://about.me/person",
                notes="done",
            )

            with open(path, "r") as f:
                contents = f.read()

            self.assertIn("timestamp,site,site_name,status,email,username,profile_url,notes", contents)
            self.assertIn("about-me,about.me,completed,person@example.com,person", contents)

    def test_generic_site_default_workflow_autofills_before_pause(self):
        site = GenericSite(
            FakeEngine(),
            captcha_solver=None,
            config_data={
                "slug": "example",
                "name": "Example",
                "signup_url": "https://example.com/join",
            },
        )

        actions = [step["action"] for step in site.config_data["steps"]]

        self.assertIn("autofill_common", actions)
        self.assertLess(actions.index("autofill_common"), actions.index("pause"))


if __name__ == "__main__":
    unittest.main()
