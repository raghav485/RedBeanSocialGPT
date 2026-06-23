# RedBeanSocialGPT

Playwright-based browser automation framework with CLI and optional Tk GUI entry points.

## Requirements

- Python 3.10+
- Playwright browsers
- Tk support in your Python installation, only if you want to use `main_gui.py`

Install Python dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Safe Smoke Test

Use this first. It launches a real Chromium browser and loads a neutral webpage without creating accounts:

```bash
venv/bin/python main.py --smoke-test
```

You can point the smoke test at another URL:

```bash
venv/bin/python main.py --smoke-test --smoke-url https://example.com
```

## List Available Sites

The app loads Python-backed sites and JSON-backed site configs from `config/sites/`.

```bash
venv/bin/python main.py --list-sites
```

## CLI Usage

```bash
venv/bin/python main.py --site about-me --num 1
venv/bin/python main.py --site github --num 1
venv/bin/python main.py --site detailerdirectory --num 1
```

Run a campaign across several sites:

```bash
venv/bin/python main.py --sites about-me,github,detailerdirectory --num 1
```

Run every configured site:

```bash
venv/bin/python main.py --sites all --num 1
```

Run a non-submitting autofill audit across the configured backlink sites:

```bash
venv/bin/python main.py --sites all --autofill-audit --audit-csv autofill_audit.csv
```

The audit opens each JSON-backed site, attempts autofill, records page status and filled field count, then closes the browser without submitting forms.

Optional flags:

```bash
--headless
--use-accounts-file
--profile config/business_profile.json
--site-config-dir config/sites
--status-csv submissions.csv
```

When `--use-accounts-file` is provided, `accounts.txt` should contain one account per line:

```text
username,password,email
```

Proxy entries can be placed in `proxy.txt`, one per line. Supported formats include:

```text
host:port
host:port:user:password
http://user:password@host:port
```

Business/listing details for generic backlink sites live in:

```bash
config/business_profile.json
```

Generic site workflows open the real signup/join page, attempt to autofill common account/listing fields, then pause for review and manual completion. They do not bypass CAPTCHA, email verification, paid review, or approval checks.

The autofill layer looks for common labels, placeholders, names, and IDs for fields such as:

```text
email, username, password, business_name, owner_name, first_name, last_name,
website, phone, address, city, state, postal_code, category, description
```

Campaign results are appended to `submissions.csv` by default. When you mark a manual-assisted site as complete, the app asks for the profile/listing URL and notes, then records them.

## GUI Usage

```bash
venv/bin/python main_gui.py
```

If you see an error about `_tkinter`, your Python installation does not include Tk support. The CLI still works; install a Python build with Tk support to use the GUI.

## Configuration

- `config/default_settings.json`: shared runtime settings
- `config/business_profile.json`: reusable business/listing data
- `config/sites/backlink_sites.json`: starter backlink website catalog
- `config/reddit.json`: Reddit workflow selectors
- `config/instagram.json`: Instagram workflow selectors
- `config/tiktok.json`: TikTok workflow selectors
- `src/engine.py`: Playwright browser wrapper
- `src/sites/`: site-specific workflow logic

## Add Another Website

Add a JSON object to a file in `config/sites/`:

```json
{
  "slug": "example-directory",
  "name": "Example Directory",
  "website_url": "https://example-directory.com",
  "signup_url": "https://example-directory.com/join",
  "category": "business-directory"
}
```

For simple manual-assisted flows, no Python code is needed. If a site has stable selectors and allows automation, add a `steps` array using actions such as `navigate`, `fill`, `click`, `wait`, `sleep`, `print`, and `pause`.

## Notes

Third-party websites frequently change selectors, CAPTCHA flows, and anti-abuse checks. Use this project only where you have permission and where your use complies with the target service's rules.
