"""Campus Customs API.

Problem 3: read-only product endpoints plus product images.
Problem 4: accounts and login (auth.py).
Problem 5: /api/chat, answered by the PydanticAI agent (agent.py, tools.py, models.py, prompts/).

Run from the backend/ folder (with hw4's venv active):
    uvicorn main:app --reload --port 8000
"""

import json
import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import UsageLimitExceeded

import agent as shop_agent
import audit
import auth
import memory
import search
from db import DATA_DIR, SIZE_ORDER, connect, short_description
from models import (
    Category,
    ChatRequest,
    ChatResponse,
    ColorFamily,
    HistoryMessage,
    ProductCard,
    SearchResponse,
    SizeName,
    SortOrder,
)
from tools import Customer, ShopDeps, check_page

log = logging.getLogger("campus_customs")
MAX_CARDS = 12  # most product cards one chat reply can put on the page


@asynccontextmanager
async def lifespan(app: FastAPI):
    auth.init_sessions_table()
    memory.init_chat_table()
    # Build the agent once at startup (reads prompts/prompt.md and the Portkey key).
    try:
        app.state.agent = shop_agent.build_agent()
    except Exception as exc:  # keep the shop up even if the key is missing
        app.state.agent = None
        log.error("Agent failed to load: %s", exc)
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)
app.include_router(auth.router)


@app.exception_handler(RequestValidationError)
async def readable_validation_error(_request: Request, exc: RequestValidationError):
    """Turn Pydantic's error list into one sentence the form can show."""
    messages = []
    for err in exc.errors():
        field = str(err["loc"][-1]).replace("_", " ").capitalize()
        msg = err["msg"].removeprefix("Value error, ")
        messages.append(f"{field}: {msg}.")
    return JSONResponse(status_code=422, content={"detail": " ".join(messages)})

# The db stores image paths as "products/<file>.jpg". Mount only the products
# folder (not all of data/, which would expose the .db file) at /media/products,
# so every image URL is /media/<image_file_path>.
app.mount("/media/products", StaticFiles(directory=DATA_DIR / "products"), name="media")


def product_summary(row: sqlite3.Row | dict) -> dict:
    colors = row["colors"] if isinstance(row["colors"], list) else json.loads(row["colors"])
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "category": search.category_of(row["garment_type"]),
        "color_family": search.color_family_of(colors),
        "short_description": short_description(row["description"]),
        "price": row["price"],
        "image_url": f"/media/{row['image_file_path']}",
        "total_stock": row["total_stock"],
        "sizes_in_stock": _sizes_in_stock(row),
    }


def _sizes_in_stock(row: sqlite3.Row | dict) -> list[str]:
    """In-stock sizes in XS→XXL order, from a search.py product or a SQL row with in_stock_csv."""
    if isinstance(row, dict) and "sizes" in row:
        return search.in_stock_sizes(row)
    sizes = set((row["in_stock_csv"] or "").split(","))
    return [s for s in SIZE_ORDER if s in sizes]


@app.get("/api/health")
def health(request: Request) -> dict:
    return {"status": "ok", "agent_loaded": request.app.state.agent is not None}


@app.get("/api/products")
def list_products() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
                   GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS in_stock_csv
            FROM catalogue c
            LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            ORDER BY c.name
            """
        ).fetchall()
    return [product_summary(r) for r in rows]


@app.get("/api/search")
def search_products(
    q: str = Query("", max_length=100),
    category: Category | None = None,
    size: SizeName | None = None,
    color: ColorFamily | None = None,
    price: str | None = Query(None, description="A price range key: under-50, 50-70, 70-plus."),
    sort: SortOrder = "relevance",
    limit: int = Query(200, ge=1, le=200),
) -> SearchResponse:
    """The site's search bar and Products-page filters. Same engine as the agent's find_products,
    so the page and the chat always agree."""
    if price is not None and price not in search.PRICE_BUCKETS:
        raise HTTPException(422, f"Price: must be one of {', '.join(search.PRICE_BUCKETS)}.")
    _, lo, hi = search.PRICE_BUCKETS[price] if price else (None, None, None)
    outcome = search.search(q, search.Filters(category, size, color, max_price=hi, min_price=lo), sort)
    return SearchResponse(
        query=q,
        total=len(outcome.products),
        products=[ProductCard(**product_summary(p)) for p in outcome.products[:limit]],
        unmatched_terms=outcome.unmatched_terms,
        matches_all_terms=outcome.matches_all_terms,
        category_counts=outcome.category_counts,
        color_counts=outcome.color_counts,
        price_counts=outcome.price_counts,
        category_labels=search.CATEGORY_LABELS,
        color_labels=search.COLOR_LABELS,
        price_labels={k: label for k, (label, _, _) in search.PRICE_BUCKETS.items()},
    )


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
                   GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS in_stock_csv
            FROM catalogue c
            LEFT JOIN inventory i ON i.product_id = c.product_id
            WHERE c.product_id = ?
            GROUP BY c.product_id
            """,
            (product_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?",
            (product_id,),
        ).fetchall()

    sizes = sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in stock),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else 99,
    )
    return {
        **product_summary(row),
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "sizes": sizes,
    }


def product_cards(product_ids: list[str]) -> list[ProductCard]:
    """Look up cards for the agent's product_ids, dropping any ID not in the catalogue."""
    ids = list(dict.fromkeys(product_ids))[:MAX_CARDS]
    if not ids:
        return []
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
                   GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS in_stock_csv
            FROM catalogue c
            LEFT JOIN inventory i ON i.product_id = c.product_id
            WHERE c.product_id IN ({",".join("?" * len(ids))})
            GROUP BY c.product_id
            """,
            ids,
        ).fetchall()
    by_id = {r["product_id"]: ProductCard(**product_summary(r)) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


@app.post("/api/chat")
async def chat(
    body: ChatRequest, request: Request, user: dict | None = Depends(auth.current_user)
) -> ChatResponse:
    agent = request.app.state.agent
    if agent is None:
        raise HTTPException(503, "The shop assistant is offline right now. Please try again later.")
    customer = Customer(**user) if user else None
    deps = ShopDeps(customer=customer, page=check_page(body.page))
    # Logged in: history comes from the database (the browser's copy is ignored, so it can't be
    # edited). Guest: nothing is stored, so use the turns the widget sent.
    history = (memory.load_agent_history(customer.id) if customer
               else shop_agent.to_message_history(body.history))
    entry = audit.new_entry(
        body.message,
        shopper=f"user {customer.id}" if customer else "guest",
        page=deps.page.product_id or deps.page.page if deps.page else "unknown",
    )
    try:
        reply = await shop_agent.chat(agent, body.message, history, deps, entry)
    except UsageLimitExceeded:
        raise HTTPException(502, "Sorry, that question took too many steps. Could you rephrase it?")
    except Exception:
        log.exception("Agent run failed")
        raise HTTPException(502, "Sorry, the assistant had trouble answering. Please try again.")
    finally:
        await audit.append(entry)  # every turn is logged, including failures
    products = product_cards(reply.product_ids)
    # A heading with no valid products would show an empty results section, so drop it.
    heading = reply.results_heading if products else None
    if customer:
        memory.save_turn(customer.id, body.message, reply.message, products, heading)
    return ChatResponse(reply=reply.message, results_heading=heading, products=products)


@app.get("/api/chat/history")
def chat_history(user: dict = Depends(auth.require_user)) -> list[HistoryMessage]:
    """The logged-in shopper's saved chat, oldest first, for the widget to redraw."""
    return memory.load_display_history(user["id"], product_cards)
