from __future__ import annotations

import json
import re
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from markdown import markdown
from slugify import slugify

import config


app = Flask(__name__)
app.secret_key = config.SECRET_KEY

DATE_FMT = "%Y-%m-%dT%H:%M:%S"
DEFAULT_NAV_LINKS = [
    {"label": "About", "url": "/about", "target": "_self"},
    {"label": "Contact", "url": "mailto:", "target": "_self"},
    {"label": "LinkedIn", "url": "", "target": "_blank"},
    {"label": "GitHub", "url": "", "target": "_blank"},
]
DEFAULT_MAIN_TITLE = config.SITE_DESCRIPTION


def ensure_data_file() -> None:
    """Make sure the posts file exists."""
    config.DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not config.DATA_PATH.exists():
        save_data(
            {
                "posts": [],
                "pages": {},
                "settings": {
                    "nav_links": DEFAULT_NAV_LINKS,
                    "main_title": DEFAULT_MAIN_TITLE,
                },
            }
        )


def load_data() -> Dict:
    ensure_data_file()
    with open(config.DATA_PATH, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    if not isinstance(raw, dict):
        raw = {"posts": raw}
    # Ensure defaults
    raw.setdefault("posts", [])
    raw.setdefault("pages", {})
    settings = raw.setdefault("settings", {})
    settings.setdefault("nav_links", DEFAULT_NAV_LINKS)
    settings.setdefault("main_title", DEFAULT_MAIN_TITLE)
    return raw


def save_data(data: Dict) -> None:
    config.DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(config.DATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_posts() -> List[Dict]:
    raw = load_data()
    posts = raw.get("posts", [])
    return sorted(posts, key=lambda p: parse_date(p.get("date")), reverse=True)


def save_posts(posts: List[Dict], data: Optional[Dict] = None) -> None:
    payload = data or load_data()
    payload["posts"] = posts
    save_data(payload)


def parse_date(date_str: Optional[str]) -> datetime:
    if not date_str:
        return datetime.min
    for fmt in (DATE_FMT, "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        return datetime.min


def format_date(date_str: Optional[str]) -> str:
    dt = parse_date(date_str)
    if dt == datetime.min:
        return ""
    return dt.strftime("%b %d, %Y")


def get_nav_links() -> List[Dict]:
    data = load_data()
    return data.get("settings", {}).get("nav_links", DEFAULT_NAV_LINKS)


def get_main_title() -> str:
    data = load_data()
    return data.get("settings", {}).get("main_title", DEFAULT_MAIN_TITLE)


def get_about_page() -> Dict:
    data = load_data()
    pages = data.get("pages", {})
    about = pages.get(
        "about",
        {
            "title": "About",
            "slug": "about",
            "content_html": "",
            "content_markdown": "",
            "updated": datetime.utcnow().replace(microsecond=0).isoformat(),
        },
    )
    return about


def is_authenticated() -> bool:
    return session.get("user") == config.ADMIN_USER


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def get_post_by_slug(slug: str) -> Optional[Dict]:
    for post in load_posts():
        if post.get("slug") == slug:
            return post
    return None


def build_excerpt(html: str, length: int = 220) -> str:
    text = re.sub(r"<[^>]+>", "", html or "").strip()
    if len(text) <= length:
        return text
    return f"{text[:length].rstrip()}…"


def parse_nav_links(raw_text: str) -> List[Dict]:
    links: List[Dict] = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 2:
            label, url = parts[0], parts[1]
            target = parts[2] if len(parts) > 2 else ("_blank" if url.startswith("http") else "_self")
            links.append({"label": label, "url": url, "target": target})
    return links or DEFAULT_NAV_LINKS


def render_markdown(md_text: str) -> str:
    return markdown(
        md_text or "",
        extensions=["fenced_code", "codehilite", "tables", "sane_lists"],
        output_format="html5",
    )


def next_id(posts: List[Dict]) -> int:
    ids = [p.get("id", 0) for p in posts]
    return max(ids) + 1 if ids else 1


@app.context_processor
def inject_globals():
    return {
        "site_title": config.SITE_TITLE,
        "site_description": config.SITE_DESCRIPTION,
        "main_title": get_main_title(),
        "format_date": format_date,
        "is_authenticated": is_authenticated,
        "build_excerpt": build_excerpt,
        "nav_links": get_nav_links(),
    }


@app.route("/")
def blog_index():
    posts = [
        p
        for p in load_posts()
        if p.get("status", "publish") == "publish" or is_authenticated()
    ]
    return render_template("blog_index.html", posts=posts)


@app.route("/about")
def about():
    page = get_about_page()
    return render_template("about.html", page=page)


@app.route("/<slug>")
def blog_post(slug: str):
    post = get_post_by_slug(slug)
    if not post:
        abort(404)
    if post.get("status") != "publish" and not is_authenticated():
        abort(404)
    return render_template("blog_post.html", post=post)


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == config.ADMIN_USER and password == config.ADMIN_PASSWORD:
            session["user"] = config.ADMIN_USER
            flash("Logged in", "success")
            return redirect(request.args.get("next") or url_for("admin_posts"))
        flash("Invalid credentials", "error")
    return render_template("admin_login.html")


@app.route("/logout")
def admin_logout():
    session.clear()
    flash("Logged out", "success")
    return redirect(url_for("blog_index"))


@app.route("/admin/posts")
@login_required
def admin_posts():
    posts = load_posts()
    return render_template("admin_posts.html", posts=posts)


@app.route("/admin/posts/new", methods=["GET", "POST"])
@login_required
def admin_new_post():
    if request.method == "POST":
        return handle_post_save()
    now = datetime.utcnow().replace(microsecond=0).isoformat()
    return render_template(
        "admin_edit.html",
        post={
            "title": "",
            "slug": "",
            "date": now,
            "status": "publish",
            "tags": [],
            "categories": [],
            "content_markdown": "",
            "content_html": "",
            "excerpt": "",
        },
        is_new=True,
    )


@app.route("/admin/posts/<slug>/edit", methods=["GET", "POST"])
@login_required
def admin_edit_post(slug: str):
    post = get_post_by_slug(slug)
    if not post:
        abort(404)
    if request.method == "POST":
        return handle_post_save(existing=post)
    return render_template("admin_edit.html", post=post, is_new=False)


def handle_post_save(existing: Optional[Dict] = None):
    posts = load_posts()
    data = load_data()
    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required", "error")
        return redirect(request.referrer or url_for("admin_posts"))

    slug_input = request.form.get("slug", "").strip()
    slug_value = slug_input or (existing.get("slug") if existing else slugify(title))
    slug_value = slugify(slug_value)

    if not slug_value:
        flash("Slug could not be generated", "error")
        return redirect(request.referrer or url_for("admin_posts"))

    # Ensure slug uniqueness
    for post in posts:
        if post.get("slug") == slug_value and (
            not existing or post.get("id") != existing.get("id")
        ):
            flash("Slug already exists", "error")
            return redirect(request.referrer or url_for("admin_posts"))

    md_body = request.form.get("content_markdown", "").strip()
    html_body = request.form.get("content_html", "").strip()
    if md_body:
        html_body = render_markdown(md_body)
    elif not html_body and existing:
        html_body = existing.get("content_html", "")

    date_str = request.form.get("date", "").strip() or datetime.utcnow().replace(
        microsecond=0
    ).isoformat()
    if parse_date(date_str) == datetime.min:
        date_str = datetime.utcnow().replace(microsecond=0).isoformat()

    tags = [
        t.strip()
        for t in request.form.get("tags", "").split(",")
        if t.strip()
    ]
    categories = [
        c.strip()
        for c in request.form.get("categories", "").split(",")
        if c.strip()
    ]
    status = request.form.get("status", "publish")
    excerpt = request.form.get("excerpt", "").strip()
    if not excerpt and html_body:
        excerpt = build_excerpt(html_body)

    payload = {
        "id": existing.get("id") if existing else next_id(posts),
        "slug": slug_value,
        "title": title,
        "date": date_str,
        "modified": datetime.utcnow().replace(microsecond=0).isoformat(),
        "status": status,
        "tags": tags,
        "categories": categories,
        "content_markdown": md_body,
        "content_html": html_body,
        "excerpt": excerpt,
        "author": existing.get("author")
        if existing
        else config.ADMIN_USER,
    }

    if existing:
        for idx, post in enumerate(posts):
            if post.get("id") == existing.get("id"):
                posts[idx] = payload
                break
        flash("Post updated", "success")
    else:
        posts.append(payload)
        flash("Post created", "success")

    save_posts(posts, data=data)
    return redirect(url_for("admin_posts"))


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    data = load_data()
    about_page = get_about_page()
    nav_links = get_nav_links()
    main_title = get_main_title()

    if request.method == "POST":
        about_html = request.form.get("about_content", "").strip()
        nav_links_raw = request.form.get("nav_links", "")
        main_title_val = request.form.get("main_title", "").strip() or DEFAULT_MAIN_TITLE
        parsed_links = parse_nav_links(nav_links_raw)

        pages = data.setdefault("pages", {})
        pages["about"] = {
            "title": about_page.get("title", "About"),
            "slug": "about",
            "content_html": about_html,
            "content_markdown": "",
            "updated": datetime.utcnow().replace(microsecond=0).isoformat(),
        }
        settings = data.setdefault("settings", {})
        settings["nav_links"] = parsed_links
        settings["main_title"] = main_title_val

        save_data(data)
        flash("Settings updated", "success")
        return redirect(url_for("admin_settings"))

    nav_links_text = "\n".join(
        f"{link.get('label','')}|{link.get('url','')}|{link.get('target','')}"
        for link in nav_links
    )
    return render_template(
        "admin_settings.html",
        about_content=about_page.get("content_html", ""),
        nav_links_text=nav_links_text,
        main_title=main_title,
    )


if __name__ == "__main__":
    app.run(debug=True)
