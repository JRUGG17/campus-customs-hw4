"""Customer memory: saves logged-in shoppers' chats in chat_messages and loads them back.

Rows follow the seed data's format: products_json is a JSON list of the product cards shown
with that message ("[]" when none). We add one nullable column, results_heading, so a reload
knows whether those products were search results on the page or small cards in the chat.
"""

import json

from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart

from db import connect
from models import HistoryMessage, ProductCard

AGENT_HISTORY_LIMIT = 20  # most recent messages the agent sees (same cap as guest history)
DISPLAY_HISTORY_LIMIT = 50  # most recent messages reloaded into the chat widget


def init_chat_table() -> None:
    with connect() as conn:
        columns = {r["name"] for r in conn.execute("PRAGMA table_info(chat_messages)")}
        if "results_heading" not in columns:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN results_heading TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)"
        )


def save_turn(
    user_id: int,
    message: str,
    reply: str,
    products: list[ProductCard],
    results_heading: str | None,
) -> None:
    """Store one shopper message and the agent's reply, in order."""
    with connect() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'user', ?, '[]')",
            (user_id, message),
        )
        conn.execute(
            """
            INSERT INTO chat_messages (user_id, role, content, products_json, results_heading)
            VALUES (?, 'assistant', ?, ?, ?)
            """,
            (user_id, reply, json.dumps([p.model_dump() for p in products]), results_heading),
        )


def _recent_rows(user_id: int, limit: int) -> list:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT role, content, products_json, results_heading, created_at
            FROM chat_messages WHERE user_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    rows = list(reversed(rows))
    # Start on a shopper message so the agent never sees a reply without its question.
    while rows and rows[0]["role"] != "user":
        rows.pop(0)
    return rows


def _shown_ids(products_json: str | None) -> list[str]:
    try:
        items = json.loads(products_json or "[]")
    except json.JSONDecodeError:
        return []
    return [p["product_id"] for p in items if isinstance(p, dict) and "product_id" in p]


def load_agent_history(user_id: int) -> list[ModelMessage]:
    """The shopper's recent turns as PydanticAI messages (server-side, so they can't be forged)."""
    messages: list[ModelMessage] = []
    for r in _recent_rows(user_id, AGENT_HISTORY_LIMIT):
        if r["role"] == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=r["content"])]))
        else:
            ids = _shown_ids(r["products_json"])
            note = f"\n[Products shown: {', '.join(ids)}]" if ids else ""
            messages.append(ModelResponse(parts=[TextPart(content=r["content"] + note)]))
    return messages


def load_display_history(user_id: int, product_cards) -> list[HistoryMessage]:
    """Recent messages for the chat widget. Cards are rebuilt from the catalogue by ID, so a
    reloaded chat shows today's prices and stock, not a stale snapshot."""
    history = []
    for r in _recent_rows(user_id, DISPLAY_HISTORY_LIMIT):
        history.append(
            HistoryMessage(
                role=r["role"],
                content=r["content"],
                results_heading=r["results_heading"],
                products=product_cards(_shown_ids(r["products_json"])),
                created_at=r["created_at"],
            )
        )
    return history


def message_count(user_id: int) -> int:
    with connect() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
