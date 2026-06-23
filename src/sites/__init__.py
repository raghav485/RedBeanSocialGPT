# src/sites package
from .registry import (
    STATIC_SITE_CLASSES,
    create_site_instance,
    get_available_site_names,
    get_site_definitions,
)

SITES_MAP = STATIC_SITE_CLASSES
