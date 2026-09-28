"""Dump recent database writes to a markdown file as evidence.

From hw4/:
    venv/bin/python scripts/db_evidence.py
Writes output/db_writes.md. Password and token hashes are truncated.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

HW4 = Path(__file__).resolve().parent.parent
DB = HW4 / "data" / "campus_customs.db"
OUT = HW4 / "output" / "db_writes.md"

QUERIES = {
    "users": """
        SELECT id, first_name, last_name, email,
               substr(password_hash, 1, 30) || '…' AS password_hash,
               created_at
        FROM users ORDER BY id
    """,
    "sessions": """
        SELECT id, user_id, substr(token_hash, 1, 16) || '…' AS token_hash,
               created_at, expires_at
        FROM sessions ORDER BY id
    """,
    "chat_messages": """
        SELECT m.id, u.first_name || ' ' || u.last_name AS shopper, m.role,
               replace(substr(m.content, 1, 70), char(10), ' ') AS content,
               json_array_length(m.products_json) AS cards, m.results_heading, m.created_at
        FROM chat_messages m JOIN users u ON u.id = m.user_id
        WHERE m.id > 22 ORDER BY m.id
    """,
}


# Demo logins shown in the README stay readable; every other address is masked (a***@yale.edu)
# because this file is published in a public repo.
DEMO_EMAILS = {"test@campuscustoms.yale.edu", "handsome.dan@yale.edu"}


def mask_email(value):
    if isinstance(value, str) and "@" in value and value not in DEMO_EMAILS:
        name, domain = value.split("@", 1)
        return f"{name[0]}***@{domain}"
    return value


def table_md(conn: sqlite3.Connection, sql: str) -> str:
    cur = conn.execute(sql)
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(mask_email(v)).replace("|", "\\|") for v in r) + " |" for r in rows]
    return "\n".join(lines)


def main() -> None:
    conn = sqlite3.connect(DB)
    existing = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    parts = [
        "# Database Writes",
        f"Snapshot of `data/campus_customs.db` taken {datetime.now():%Y-%m-%d %H:%M}. "
        "Hashes are truncated; plain-text passwords and session tokens are never stored. "
        "Emails other than the two demo logins are masked for the public repo.",
    ]
    for name, sql in QUERIES.items():
        if name in existing:
            parts.append(f"## `{name}`\n\n```sql\n{' '.join(sql.split())}\n```\n\n{table_md(conn, sql)}")
    OUT.write_text("\n\n".join(parts) + "\n")
    print(f"wrote {OUT.relative_to(HW4)}")


if __name__ == "__main__":
    main()
