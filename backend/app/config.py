from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]

BASE_DIR = Path(__file__).resolve().parent.parent.parent

if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env", override=False)

APP_ENV = os.getenv("APP_ENV", os.getenv("RENDER_ENV", "development")).strip().lower()

_default_data_dir = Path("/tmp/qazaq-locqa-data") if os.getenv("VERCEL") else (BASE_DIR / "data")
DATA_DIR = Path(os.getenv("QAZAQ_LOCQA_DATA_DIR", str(_default_data_dir)))
UPLOADS_DIR = DATA_DIR / "uploads"
DEMO_DIR = BASE_DIR / "data" / "demo"
REPORTS_DIR = (DATA_DIR / "reports") if os.getenv("VERCEL") else (BASE_DIR / "reports")
GLOSSARY_DIR = BASE_DIR / "glossary"

for directory in (DATA_DIR, UPLOADS_DIR, DEMO_DIR, REPORTS_DIR, GLOSSARY_DIR):
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Cloud read-only container paths fall back cleanly to PostgreSQL persistence
        pass


def normalize_database_url(raw_url: str) -> str:
    """
    Normalize cloud database URLs (Render, Neon, Supabase, Railway, Heroku)
    for SQLAlchemy 2.0 + psycopg v3 driver while preserving SQLite URLs.
    """
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+psycopg://" + url[len("postgresql+psycopg2://") :]
    return url


DEFAULT_DB_PATH = DATA_DIR / "qazaq_locqa.db"
_raw_db_url = (
    os.getenv("QAZAQ_LOCQA_DB_URL")
    or os.getenv("DATABASE_URL")
    or f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
)
DATABASE_URL = normalize_database_url(_raw_db_url)

MAX_UPLOAD_MB = int(os.getenv("QAZAQ_LOCQA_MAX_UPLOAD_MB", "25"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

ALLOWED_ARB_EXTENSIONS = {".arb", ".json"}
ALLOWED_CSV_EXTENSIONS = {".csv"}

_DEFAULT_DEV_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:4173,http://127.0.0.1:4173"
)
_raw_cors = os.getenv("CORS_ORIGINS") or os.getenv("QAZAQ_LOCQA_CORS_ORIGINS") or _DEFAULT_DEV_ORIGINS

CORS_ORIGINS = list(
    dict.fromkeys(
        origin.strip().rstrip("/")
        for origin in f"{_raw_cors},{_DEFAULT_DEV_ORIGINS}".split(",")
        if origin.strip()
    )
)

# Optional regex for preview/production/tunnel domains (e.g. *.vercel.app, *.trycloudflare.com, *.loca.lt)
CORS_ORIGIN_REGEX: str | None = (
    os.getenv("CORS_ORIGIN_REGEX", r"^https://.*\.(vercel\.app|trycloudflare\.com|loca\.lt)$").strip() or None
)
