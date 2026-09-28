"""Append-only audit trail of agent-loop activity: output/audit_trail.json.

One entry per chat turn:
    time, run_id, shopper (user id or "guest"), page, message (redacted, trimmed),
    steps: one per model response -> tool calls with short args and short results,
    stop_reason: final_result | content_filter | usage_limit | error,
    duration_s, model_requests, input/output tokens, model.

The file is a JSON array that only ever grows: entries are appended under a lock and written
via a temp file + rename, so a crash mid-write can't truncate earlier history. Nothing in the
app deletes or rewrites old entries.
"""

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
_lock = asyncio.Lock()

_CARD = re.compile(r"\b\d(?:[ -]?\d){11,18}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def redact(text: str, limit: int = 200) -> str:
    """Keep card numbers and email addresses out of the log, and keep entries short."""
    text = _CARD.sub("[card number removed]", text)
    text = _EMAIL.sub("[email]", text)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _short(value, limit: int = 240) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    if isinstance(value, dict):
        value = _summarize_result(value)
    return redact(value if isinstance(value, str) else json.dumps(value, default=str), limit)


def _summarize_result(r: dict):
    """Compact the fields a reviewer cares about from each tool's result."""
    if "matches" in r:  # find_products: keep the numbers the agent may quote
        top = [
            {"id": m["product_id"], "price": m["price"],
             **({"qty_in_size": m["quantity_in_size"]} if m.get("quantity_in_size") is not None else {})}
            for m in r["matches"][:3]
        ]
        return {"total_matches": r["total_matches"], "price_range": [r.get("price_min"), r.get("price_max")],
                "removed_by_filters": r.get("removed_by_filters"),
                "unmatched_terms": r.get("unmatched_terms"), "top": top}
    if "alternatives" in r:  # find_alternatives
        return {"wanted": r["wanted"], "status": r["wanted_status"],
                "alternatives": [a["product"]["product_id"] for a in r["alternatives"]]}
    if "requested_size" in r:  # check_size_stock
        return {"product_id": r["product_id"], "size": r["size"], "quantity": r["quantity"],
                "status": r["status"], "price": r["price"]}
    if "sizes_sold_out" in r:  # get_product_details
        return {"product_id": r["product_id"], "price": r["price"], "total_stock": r["total_stock"],
                "sold_out": r["sizes_sold_out"]}
    if "member_since" in r:  # get_customer_profile: never log the email itself
        return {"first_name": r["first_name"], "member_since": r["member_since"]}
    return r


def steps_from(messages: list[ModelMessage]) -> list[dict]:
    """Turn one run's new messages into agent-loop steps (one per model response)."""
    results: dict[str, str] = {}
    for m in messages:
        if isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, ToolReturnPart):
                    results[p.tool_call_id] = _short(p.content)
                elif isinstance(p, RetryPromptPart) and p.tool_call_id:
                    results[p.tool_call_id] = "retry: " + _short(p.content, 120)
    steps = []
    for m in messages:
        if not isinstance(m, ModelResponse):
            continue
        calls = [p for p in m.parts if isinstance(p, ToolCallPart)]
        text = " ".join(p.content for p in m.parts if isinstance(p, TextPart)).strip()
        steps.append({
            "time": m.timestamp.astimezone(timezone.utc).isoformat(timespec="seconds"),
            "tool_calls": [
                {
                    "tool": c.tool_name,
                    "args": _short(c.args_as_dict(), 160),
                    "result": ("(final answer)" if c.tool_name == "final_result"
                               else results.get(c.tool_call_id, "(no result)")),
                }
                for c in calls
            ],
            **({"text": redact(text, 120)} if text else {}),
        })
    return steps


def new_entry(message: str, shopper: str, page: str) -> dict:
    return {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": uuid.uuid4().hex[:8],
        "shopper": shopper,
        "page": page,
        "message": redact(message),
        "model": os.getenv("PORTKEY_MODEL", "gpt-5.6 luna"),
    }


async def append(entry: dict) -> None:
    async with _lock:
        AUDIT_PATH.parent.mkdir(exist_ok=True)
        try:
            entries = json.loads(AUDIT_PATH.read_text()) if AUDIT_PATH.exists() else []
            if not isinstance(entries, list):
                raise ValueError("audit trail is not a JSON array")
        except (json.JSONDecodeError, ValueError):
            # Never overwrite a file we can't read: set it aside and start a new one.
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            AUDIT_PATH.rename(AUDIT_PATH.with_name(f"audit_trail.unreadable-{stamp}.json"))
            entries = []
        entries.append(entry)
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(entries, indent=2))
        tmp.replace(AUDIT_PATH)
