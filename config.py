import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "posts.json"

# Site metadata
SITE_TITLE = "bareblog"
SITE_DESCRIPTION = "bareblog description"

# Auth / session
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
ADMIN_USER = os.getenv("ADMIN_USER", "admin@bareblog.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "bareblog123")
