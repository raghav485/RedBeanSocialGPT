import json
from pathlib import Path

from .generic import GenericSite
from .instagram import InstagramSite
from .reddit import RedditSite
from .tiktok import TikTokSite


STATIC_SITE_CLASSES = {
    "instagram": InstagramSite,
    "reddit": RedditSite,
    "tiktok": TikTokSite,
}

DEFAULT_SITE_CONFIG_DIR = Path("config/sites")


def load_json_site_configs(site_config_dir=DEFAULT_SITE_CONFIG_DIR):
    config_dir = Path(site_config_dir)
    configs = {}
    if not config_dir.exists():
        return configs

    for path in sorted(config_dir.glob("*.json")):
        try:
            with path.open("r") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"Warning: failed to load site config {path}: {exc}")
            continue

        site_entries = data.get("sites") if isinstance(data.get("sites"), list) else [data]
        for entry in site_entries:
            slug = entry.get("slug") or path.stem
            configs[slug.lower()] = {
                "path": str(path),
                "config_data": entry,
                "name": entry.get("name", slug),
                "website_url": entry.get("website_url", ""),
                "signup_url": entry.get("signup_url", ""),
                "category": entry.get("category", "custom"),
                "runner": "json",
            }

    return configs


def get_site_definitions(site_config_dir=DEFAULT_SITE_CONFIG_DIR):
    definitions = {
        slug: {
            "name": site_class.__name__.replace("Site", ""),
            "website_url": "",
            "signup_url": "",
            "category": "legacy",
            "runner": "python",
        }
        for slug, site_class in STATIC_SITE_CLASSES.items()
    }
    definitions.update(load_json_site_configs(site_config_dir))
    return dict(sorted(definitions.items()))


def get_available_site_names(site_config_dir=DEFAULT_SITE_CONFIG_DIR):
    return list(get_site_definitions(site_config_dir).keys())


def create_site_instance(site_name, engine, captcha_solver, temp_mail_client=None, site_config_dir=DEFAULT_SITE_CONFIG_DIR):
    slug = site_name.lower()
    if slug in STATIC_SITE_CLASSES:
        return STATIC_SITE_CLASSES[slug](engine, captcha_solver, temp_mail_client)

    json_configs = load_json_site_configs(site_config_dir)
    config = json_configs.get(slug)
    if config:
        return GenericSite(
            engine,
            captcha_solver,
            temp_mail_client,
            config_path=None,
            config_data=config["config_data"]
        )

    return None
