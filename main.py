import os
import csv
import json
import argparse
import random
import string
from datetime import datetime, timezone
from src.engine import PlaywrightEngine
from src.proxy_manager import ProxyManager
from src.temp_mail import TempMail
from src.captcha import CaptchaSolver
from src.sites import create_site_instance, get_available_site_names, get_site_definitions
from src.submission_tracker import append_submission

# Load default settings
def load_settings():
    settings_path = 'config/default_settings.json'
    defaults = {
        "headless": False,
        "default_timeout_ms": 30000,
        "capmonster_key": "",
        "use_free_mail": True,
        "output_csv": "accounts.csv",
        "user_agent": None
    }
    if os.path.exists(settings_path):
        try:
            with open(settings_path, 'r') as f:
                config = json.load(f)
                defaults.update(config)
        except Exception as e:
            print(f"Warning: Failed to load default settings: {e}")
    return defaults

def load_profile(profile_path):
    defaults = {
        "business_name": "",
        "owner_name": "",
        "first_name": "",
        "last_name": "",
        "job_title": "Owner",
        "website": "",
        "phone": "",
        "address": "",
        "city": "",
        "state": "",
        "postal_code": "",
        "country": "United States",
        "category": "",
        "description": "",
        "logo_path": "",
    }
    if not profile_path:
        return defaults
    if os.path.exists(profile_path):
        try:
            with open(profile_path, 'r') as f:
                defaults.update(json.load(f))
        except Exception as e:
            print(f"Warning: Failed to load profile data: {e}")
    return defaults

# Helper to generate random password
def generate_random_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$"
    return ''.join(random.choices(chars, k=length))

# Helper to generate random username
def generate_random_username(length=10):
    return ''.join(random.choices(string.ascii_lowercase, k=length)) + str(random.randint(100, 999))

def resolve_selected_sites(site, sites_arg, available_sites):
    if sites_arg:
        requested = []
        for raw_site in sites_arg.split(","):
            site_slug = raw_site.strip().lower()
            if not site_slug:
                continue
            if site_slug == "all":
                requested.extend(available_sites)
            else:
                requested.append(site_slug)
    elif site:
        requested = [site.lower()]
    else:
        requested = []

    selected = []
    seen = set()
    for site_slug in requested:
        if site_slug not in seen:
            selected.append(site_slug)
            seen.add(site_slug)
    return selected

def register_account(site_name, email, username, password, settings, selected_proxy=None, extra_context=None, return_result=False):
    """
    Handles a single account registration.
    """
    print(f"\n--- Registering {site_name.upper()} Account: {username} ---")
    print(f"Email: {email}")
    if selected_proxy:
        print(f"Using Proxy: {selected_proxy['server']}")
    else:
        print("Using direct connection (No Proxy)")

    # 1. Initialize engine
    engine = PlaywrightEngine(
        headless=settings["headless"],
        proxy=selected_proxy,
        user_agent=settings["user_agent"],
        timeout_ms=settings["default_timeout_ms"]
    )
    
    # 2. Instantiate solver and site
    captcha_solver = CaptchaSolver(capmonster_key=settings.get("capmonster_key"))
    
    # Initialize temp mail if we are using it
    temp_mail_client = None
    if settings["use_free_mail"]:
        temp_mail_client = TempMail()
        # Bind the specific email address
        parts = email.split('@')
        if len(parts) == 2:
            temp_mail_client.login, temp_mail_client.domain = parts
            temp_mail_client.email_address = email

    site_inst = create_site_instance(
        site_name,
        engine,
        captcha_solver,
        temp_mail_client,
        site_config_dir=settings.get("site_config_dir", "config/sites")
    )
    if not site_inst:
        print(f"Error: Site class for '{site_name}' not found.")
        return False

    # 3. Execute
    success = False
    result_details = {}
    try:
        engine.start()
        success = site_inst.run(email, username, password, extra_context=extra_context)
        result_details = getattr(site_inst, "result_details", {}) or {}
    except Exception as e:
        print(f"Registration execution crashed: {e}")
    finally:
        engine.stop()

    result = {
        "success": success,
        "site": site_name.lower(),
        "site_name": getattr(site_inst, "config_data", {}).get("name", site_name),
        "details": result_details,
    }
    return result if return_result else success

def run_browser_smoke_test(settings, url="https://example.com"):
    """
    Launches a real Playwright browser, loads a neutral page, and verifies that
    navigation works without creating accounts on third-party services.
    """
    print(f"Running browser smoke test against {url}")
    engine = PlaywrightEngine(
        headless=True,
        proxy=None,
        user_agent=settings["user_agent"],
        timeout_ms=settings["default_timeout_ms"]
    )

    try:
        page = engine.start()
        page.goto(url, wait_until="domcontentloaded")
        title = page.title()
        print(f"Browser launched successfully. Page title: {title!r}")
        return True
    except Exception as e:
        print(f"Browser smoke test failed: {e}")
        return False
    finally:
        engine.stop()

def get_audit_account(use_accounts_file=False):
    if use_accounts_file and os.path.exists("accounts.txt") and os.path.getsize("accounts.txt") > 0:
        with open("accounts.txt", "r") as f:
            for line in f:
                line = line.strip()
                if not line or "," not in line:
                    continue
                parts = [part.strip() for part in line.split(",")]
                if len(parts) == 3:
                    username, password, email = parts
                    return email, username, password
    return "audit@example.com", "audituser", "AuditPassword123!"

def append_autofill_audit_row(path, row):
    fieldnames = [
        "timestamp",
        "site",
        "site_name",
        "status",
        "filled_count",
        "title",
        "final_url",
        "signup_url",
        "error",
    ]
    file_exists = os.path.exists(path)
    with open(path, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def run_autofill_audit(selected_sites, settings, profile, audit_csv, definitions, use_accounts_file=False, timeout_ms=15000):
    email, username, password = get_audit_account(use_accounts_file)
    audit_settings = settings.copy()
    audit_settings["headless"] = True
    audit_settings["default_timeout_ms"] = timeout_ms

    attempted = 0
    loaded = 0
    filled_total = 0
    for site_name in selected_sites:
        definition = definitions.get(site_name, {})
        if definition.get("runner") != "json":
            print(f"Skipping {site_name}: autofill audit only runs JSON-backed backlink sites.")
            continue

        attempted += 1
        site_label = definition.get("name", site_name)
        signup_url = definition.get("signup_url", "")
        print(f"\n[AUDIT] {site_label} ({site_name})")

        engine = PlaywrightEngine(
            headless=audit_settings["headless"],
            proxy=None,
            user_agent=audit_settings["user_agent"],
            timeout_ms=audit_settings["default_timeout_ms"]
        )
        captcha_solver = CaptchaSolver(capmonster_key=audit_settings.get("capmonster_key"))
        site_inst = create_site_instance(
            site_name,
            engine,
            captcha_solver,
            temp_mail_client=None,
            site_config_dir=audit_settings.get("site_config_dir", "config/sites")
        )

        status = "error"
        title = ""
        final_url = ""
        error = ""
        filled_count = 0
        try:
            if not site_inst or not signup_url:
                raise RuntimeError("Missing site config or signup_url")

            engine.start()
            site_inst.workflow_context = site_inst.build_context(email, username, password, profile)
            site_inst.last_autofill_count = 0
            audit_steps = site_inst.config_data.get("audit_steps") or site_inst.config_data.get("steps")
            if not audit_steps:
                audit_steps = [
                    {"action": "navigate", "url": "{signup_url}"},
                    {"action": "sleep", "seconds": 2},
                    {"action": "autofill_common"},
                ]
            site_inst.execute_steps(audit_steps, skip_pause=True)
            filled_count = site_inst.last_autofill_count
            title = engine.page.title()
            final_url = engine.page.url
            status = "loaded"
            loaded += 1
            filled_total += filled_count
        except Exception as exc:
            error = str(exc)
            print(f"[AUDIT] Failed: {error}")
        finally:
            engine.stop()

        append_autofill_audit_row(audit_csv, {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "site": site_name,
            "site_name": site_label,
            "status": status,
            "filled_count": filled_count,
            "title": title,
            "final_url": final_url,
            "signup_url": signup_url,
            "error": error,
        })
        print(f"[AUDIT] {status}; filled={filled_count}; title={title!r}")

    print(f"\nAutofill audit complete. Loaded {loaded}/{attempted} JSON-backed sites.")
    print(f"Total fields filled: {filled_total}")
    print(f"Audit saved to {audit_csv}")
    return attempted == loaded

def main():
    parser = argparse.ArgumentParser(description="Multi-site Account Generator Framework (Playwright)")
    parser.add_argument("--site", type=str, help="The platform/site slug to generate an account for")
    parser.add_argument("--sites", type=str, help="Comma-separated site slugs, or 'all', for campaign mode")
    parser.add_argument("--num", type=int, default=1, help="Number of accounts to generate")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode (Manual CAPTCHA verification will not be visible)")
    parser.add_argument("--use-accounts-file", action="store_true", help="Read account credentials from accounts.txt")
    parser.add_argument("--profile", default="config/business_profile.json", help="JSON file with business/listing data used by generic site workflows")
    parser.add_argument("--site-config-dir", default="config/sites", help="Directory containing JSON site workflow configs")
    parser.add_argument("--status-csv", default="submissions.csv", help="CSV file used to track campaign results")
    parser.add_argument("--autofill-audit", action="store_true", help="Load selected JSON-backed sites, attempt autofill, and save a non-submitting audit CSV")
    parser.add_argument("--audit-csv", default="autofill_audit.csv", help="CSV file used by --autofill-audit")
    parser.add_argument("--audit-timeout-ms", type=int, default=15000, help="Per-page timeout used by --autofill-audit")
    parser.add_argument("--list-sites", action="store_true", help="List all configured site slugs and exit")
    parser.add_argument("--smoke-test", action="store_true", help="Launch a browser and load a neutral test page without creating accounts")
    parser.add_argument("--smoke-url", default="https://example.com", help="URL used by --smoke-test")
    
    args = parser.parse_args()
    settings = load_settings()
    settings["site_config_dir"] = args.site_config_dir

    # Override headless if set via CLI
    if args.headless:
        settings["headless"] = True

    if args.list_sites:
        definitions = get_site_definitions(args.site_config_dir)
        print("Available sites:")
        for slug, definition in definitions.items():
            print(f"- {slug}: {definition['name']} ({definition['runner']})")
        raise SystemExit(0)

    if args.smoke_test:
        raise SystemExit(0 if run_browser_smoke_test(settings, args.smoke_url) else 1)

    available_sites = get_available_site_names(args.site_config_dir)
    selected_sites = resolve_selected_sites(args.site, args.sites, available_sites)
    if not selected_sites:
        parser.error("--site or --sites is required unless --smoke-test is used")

    unknown_sites = [site for site in selected_sites if site not in available_sites]
    if unknown_sites:
        parser.error(f"Unknown site(s): {', '.join(unknown_sites)}. Run --list-sites to see configured sites.")

    if args.num < 1:
        parser.error("--num must be an integer greater than 0")

    profile = load_profile(args.profile)
    definitions = get_site_definitions(args.site_config_dir)

    if args.autofill_audit:
        json_sites = [site for site in selected_sites if definitions.get(site, {}).get("runner") == "json"]
        if not json_sites:
            parser.error("--autofill-audit needs at least one JSON-backed site")
        raise SystemExit(0 if run_autofill_audit(
            json_sites,
            settings,
            profile,
            args.audit_csv,
            definitions,
            use_accounts_file=args.use_accounts_file,
            timeout_ms=args.audit_timeout_ms
        ) else 1)

    # Read proxies
    proxy_manager = ProxyManager('proxy.txt')
    print(f"Loaded {len(proxy_manager.proxies)} proxies from proxy.txt")

    accounts_to_create = []

    if args.use_accounts_file:
        accounts_file = 'accounts.txt'
        if os.path.exists(accounts_file) and os.path.getsize(accounts_file) > 0:
            with open(accounts_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and ',' in line:
                        parts = line.split(',')
                        if len(parts) == 3:
                            u, p, e = parts
                            accounts_to_create.append((e.strip(), u.strip(), p.strip()))
        else:
            print("Warning: accounts.txt is empty or missing. Falling back to dynamic generation.")

    # If list is still empty, populate dynamically
    if not accounts_to_create:
        settings["use_free_mail"] = True
        print("Using dynamic credentials and free temp-mail service.")
        for _ in range(args.num):
            temp_mail = TempMail()
            email = temp_mail.generate_email()
            username = generate_random_username()
            password = generate_random_password()
            accounts_to_create.append((email, username, password))
    else:
        # If we read from file, set use_free_mail according to config
        settings["use_free_mail"] = False

    success_count = 0
    attempt_count = 0
    for email, username, password in accounts_to_create[:args.num]:
        for site_name in selected_sites:
            attempt_count += 1
            selected_proxy = proxy_manager.get_random_proxy()
            result = register_account(
                site_name,
                email,
                username,
                password,
                settings,
                selected_proxy,
                extra_context=profile,
                return_result=True
            )
            is_success = result["success"]
            details = result.get("details", {})
            site_label = definitions.get(site_name, {}).get("name", site_name)
            status = "completed" if is_success else "needs_followup"

            append_submission(
                args.status_csv,
                site=site_name,
                site_name=site_label,
                status=status,
                email=email,
                username=username,
                profile_url=details.get("profile_url", ""),
                notes=details.get("notes", ""),
            )

            if is_success:
                success_count += 1
                print(f"Success! Account/listing completed for {site_label}: {username}")
                output_csv = settings.get("output_csv", "accounts.csv")
                file_exists = os.path.exists(output_csv)
                with open(output_csv, mode='a', newline='') as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['Email', 'Username', 'Password', 'Site'])
                    writer.writerow([email, username, password, site_name])
            else:
                print(f"Needs follow-up for {site_label}: {username}")

    print(f"\nCompleted! Marked {success_count}/{attempt_count} site attempts complete.")
    print(f"Campaign status saved to {args.status_csv}")

if __name__ == "__main__":
    main()
