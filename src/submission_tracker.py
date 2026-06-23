import csv
import os
from datetime import datetime, timezone


FIELDNAMES = [
    "timestamp",
    "site",
    "site_name",
    "status",
    "email",
    "username",
    "profile_url",
    "notes",
]


def append_submission(path, site, site_name, status, email, username, profile_url="", notes=""):
    file_exists = os.path.exists(path)
    with open(path, mode="a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "site": site,
            "site_name": site_name,
            "status": status,
            "email": email,
            "username": username,
            "profile_url": profile_url,
            "notes": notes,
        })
