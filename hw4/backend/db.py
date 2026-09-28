import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


def short_description(text: str, limit: int = 110) -> str:
    """First sentence of the description, trimmed for product cards."""
    first = text.split(". ")[0].rstrip(".") + "."
    if len(first) <= limit:
        return first
    return first[:limit].rsplit(" ", 1)[0] + "…"


def connect() -> sqlite3.Connection:
    """Open the shop db. Use as `with connect() as conn:` so writes commit."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
