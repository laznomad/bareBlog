"""
Import posts from a WordPress WXR export into data/posts.json.

Usage:
    python import_wp.py xxxxx.WordPress.xxxx-xx-xx.xml
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET

from slugify import slugify

import config


NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "wp": "http://wordpress.org/export/1.2/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
}


DEFAULT_NAV = [
    {"label": "About", "url": "/about", "target": "_self"},
    {"label": "Contact", "url": "mailto:", "target": "_self"},
    {"label": "LinkedIn", "url": "", "target": "_blank"},
    {"label": "GitHub", "url": "", "target": "_blank"},
]


def to_iso(date_str: str) -> str:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S%z"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=None).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(date_str).isoformat()
    except ValueError:
        return datetime.utcnow().replace(microsecond=0).isoformat()


def parse_posts(xml_path: Path) -> List[Dict]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    channel = root.find("channel")
    posts: List[Dict] = []

    for item in channel.findall("item"):
        post_type = item.findtext("wp:post_type", default="", namespaces=NS)
        if post_type != "post":
            continue

        status = item.findtext("wp:status", default="publish", namespaces=NS)
        post_id = int(item.findtext("wp:post_id", default="0", namespaces=NS) or 0)
        title = item.findtext("title", default="") or ""
        slug_val = item.findtext("wp:post_name", default="", namespaces=NS) or slugify(
            title
        )

        post_date = item.findtext("wp:post_date", default="", namespaces=NS)
        date_iso = to_iso(post_date) if post_date else datetime.utcnow().isoformat()
        content_html = item.findtext("content:encoded", default="", namespaces=NS) or ""
        excerpt_html = item.findtext("excerpt:encoded", default="", namespaces=NS) or ""
        author = item.findtext("dc:creator", default="", namespaces=NS) or ""

        tags = []
        categories = []
        for cat in item.findall("category"):
            domain = cat.get("domain", "")
            label = (cat.text or "").strip()
            if not label:
                continue
            if domain == "post_tag":
                tags.append(label)
            elif domain == "category":
                categories.append(label)

        posts.append(
            {
                "id": post_id,
                "slug": slug_val,
                "title": title,
                "date": date_iso,
                "modified": date_iso,
                "status": status,
                "tags": tags,
                "categories": categories,
                "content_markdown": "",
                "content_html": content_html,
                "excerpt": excerpt_html,
                "author": author,
            }
        )

    posts.sort(key=lambda p: p.get("date", ""), reverse=True)
    return posts


def parse_pages(xml_path: Path) -> Dict:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    channel = root.find("channel")
    pages: Dict[str, Dict] = {}

    for item in channel.findall("item"):
        post_type = item.findtext("wp:post_type", default="", namespaces=NS)
        if post_type != "page":
            continue

        slug_val = item.findtext("wp:post_name", default="", namespaces=NS) or ""
        title = item.findtext("title", default="") or ""
        content_html = item.findtext("content:encoded", default="", namespaces=NS) or ""
        if slug_val:
            pages[slug_val] = {
                "title": title or slug_val.title(),
                "slug": slug_val,
                "content_html": content_html,
                "content_markdown": "",
                "updated": datetime.utcnow().replace(microsecond=0).isoformat(),
            }
    return pages


def main():
    parser = argparse.ArgumentParser(description="Import WordPress export to JSON")
    parser.add_argument(
        "xml_path",
        nargs="?",
        default="",
        help="Path to the WXR xml file",
    )
    args = parser.parse_args()

    xml_path = Path(args.xml_path)
    if not xml_path.exists():
        raise SystemExit(f"File not found: {xml_path}")

    posts = parse_posts(xml_path)
    pages = parse_pages(xml_path)
    config.DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.DATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "posts": posts,
                "pages": pages,
                "settings": {
                    "nav_links": DEFAULT_NAV,
                    "main_title": "",
                },
            },
            fh,
            indent=2,
        )

    print(f"Wrote {len(posts)} posts and {len(pages)} pages to {config.DATA_PATH}")


if __name__ == "__main__":
    main()
