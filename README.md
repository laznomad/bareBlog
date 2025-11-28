# bareBlog (minimal file-based Flask blog engine)

Lightweight Flask blog engine with file-backed posts, admin login, and Markdown support for new posts.

## Quick start

1) Python 3.14 (or latest 3.x) and virtualenv:
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2) Import existing posts from the WordPress export (already run once, rerun if needed):
```sh
python import_wp.py xxxx.xml
```
This writes `data/posts.json`.

If you already have `data/posts.json` from an older run, migrate it to include the About page and nav links:
```sh
python migrate_data.py xxxx.xml
```

3) Run the app:
```sh
FLASK_APP=app.py flask run --port 5000
```
Then open `http://localhost:5000` (home/blog index).

## Admin

- Login: `http://localhost:5000/admin`
- User: `admin@bareblog.com`
- Password: `bareblog123`
- Auth data and secret key can be overridden via `ADMIN_USER`, `ADMIN_PASSWORD`, and `SECRET_KEY` env vars.

## Posts

- Stored in `data/posts.json` (no database needed).
- Imported posts keep original HTML. New posts can be written in Markdown (rendered to HTML on save) or plain HTML.
- Blog index shows published posts; drafts are visible when logged in.
