"""
One-time migration helper to upgrade an existing data/posts.json
to include pages (e.g., About) and nav links settings.

Usage:
    python migrate_data.py 
"""

import json
import sys
from pathlib import Path

import config
import import_wp


def load_json(path: Path):
    if not path.exists():
        raise SystemExit(f"Data file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok==True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def main():
    xml_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        ""
    )
    if not xml_path.exists():
        raise SystemExit(f"XML export not found: {xml_path}")

    data = load_json(config.DATA_PATH)
    if not isinstance(data, dict):
        data = {"posts": data}

    data.setdefault("posts", [])
    data.setdefault("pages", {})
    data.setdefault("settings", {})

    # Add pages (About, etc.) from the export if missing
    pages_from_xml = import_wp.parse_pages(xml_path)
    if not data["pages"]:
        data["pages"] = pages_from_xml
    else:
        for slug, page in pages_from_xml.items():
            data["pages"].setdefault(slug, page)

    # Nav links defaults
    settings = data["settings"]
    settings.setdefault("nav_links", import_wp.DEFAULT_NAV)
    settings.setdefault("main_title", "")

    save_json(config.DATA_PATH, data)
    print(
        f"Migrated data at {config.DATA_PATH}: "
        f"{len(data['posts'])} posts, {len(data['pages'])} pages, "
        f"{len(settings['nav_links'])} nav links."
    )


if __name__ == "__main__":
    main()
