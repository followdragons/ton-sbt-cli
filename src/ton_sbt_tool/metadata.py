from __future__ import annotations

from urllib.parse import urlparse

from ton_sbt_tool.config import Settings


def is_fixed_item_metadata_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    path = parsed.path.rstrip()
    if not path or path.endswith("/"):
        return False
    last_segment = path.rsplit("/", 1)[-1]
    return "." in last_segment


def get_item_metadata_mode(settings: Settings) -> str:
    if is_fixed_item_metadata_url(settings.items_base_url):
        return "fixed-file"
    return "prefix"


def get_collection_common_content_url(settings: Settings) -> str:
    if get_item_metadata_mode(settings) == "fixed-file":
        return ""
    return settings.items_base_url


def make_item_suffix(settings: Settings, item_index: int) -> str:
    if get_item_metadata_mode(settings) == "fixed-file":
        return settings.items_base_url
    if settings.item_metadata_suffix:
        return settings.item_metadata_suffix
    return f"{item_index}.json"
