"""Model setup, per-run dependencies, and the tools the agent can call.

Tools (all read-only):
  get_store_info       verified shop facts (Problem 5)
  find_products        keyword search over the catalogue -> product_ids (Problem 6)
  get_product_details  description, price, colors, stock for every size (Problem 6)
  check_size_stock     stock for one size, with the shopper's wording normalized (Problem 6)
  find_alternatives    in-stock substitutes when a size is sold out or nothing matches (Problem 9)
  (find_products gained category / size / color / price / sort filters in Problem 9)
  get_customer_profile the logged-in shopper's own account details (Problem 8)
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import ModelRetry, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

import memory
import search
from db import SIZE_ORDER, short_description
from models import (
    Alternative,
    AlternativesResult,
    Category,
    ColorFamily,
    CustomerProfile,
    PageContext,
    ProductDetails,
    ProductMatch,
    ProductSearchResult,
    SizeAvailability,
    SortOrder,
    StoreInfo,
)

BACKEND_DIR = Path(__file__).resolve().parent
HW4_DIR = BACKEND_DIR.parent

# hw4/.env first, then the repo-root .env; neither overrides a key already in the shell.
load_dotenv(HW4_DIR / ".env")
load_dotenv(HW4_DIR.parent.parent / ".env")

MAX_RESULTS = 12


@dataclass
class Customer:
    """The logged-in shopper, loaded server-side from the session cookie (never from the browser)."""

    id: int
    first_name: str
    last_name: str
    email: str
    created_at: str


@dataclass
class PageView:
    """The browser's PageContext after server-side checks: unknown IDs and paths are dropped."""

    page: str  # "home", "products", "product", "about", "login", "create-account", "other"
    product_id: str | None = None
    product_name: str | None = None
    visible_product_ids: list[str] | None = None


@dataclass
class ShopDeps:
    """Per-request context handed to every tool call and to the dynamic instructions."""

    customer: Customer | None = None
    page: PageView | None = None

    @property
    def user_id(self) -> int | None:
        return self.customer.id if self.customer else None


def make_model() -> OpenAIChatModel:
    """OpenAI through Portkey (see AGENTS.md)."""
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Add it to hw4/.env or the repo-root .env.")
    return OpenAIChatModel(
        os.getenv("PORTKEY_MODEL", "gpt-5.6 luna"),
        provider=OpenAIProvider(
            openai_client=AsyncOpenAI(
                base_url=os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1"),
                api_key=api_key,
                default_headers={
                    "x-portkey-api-key": api_key,
                    "x-portkey-provider": "openai",
                    # Measurements set this so Portkey's cache doesn't hide real response times.
                    **({"x-portkey-cache-force-refresh": "true"} if os.getenv("PORTKEY_SKIP_CACHE") else {}),
                },
            )
        ),
    )


# ---------- store facts ----------

STORE_INFO = StoreInfo(
    name="Campus Customs (Yale Bulldog Blue)",
    address="57 Broadway, New Haven, CT 06511",
    founded=1975,
    about="Family-run Yale merchandise shop across the street from campus since 1975.",
    services=[
        "Officially licensed Yale apparel",
        "In-house screen printing and embroidery",
        "Residential college, sports, and graduate school designs",
    ],
    sizes_offered=SIZE_ORDER,
)


def get_store_info(ctx: RunContext[ShopDeps]) -> StoreInfo:
    """Verified facts about Campus Customs: name, address, history, services, and sizes offered.

    Call this before answering questions about the shop itself (where it is, how long it has
    been around, what it does). Do not state shop facts that are not in this result.
    """
    return STORE_INFO


# ---------- catalogue helpers ----------


def _get_product(product_id: str) -> dict:
    for p in search.load_catalogue():
        if p["product_id"] == product_id:
            return p
    raise ModelRetry(
        f"No product has product_id {product_id!r}. Call find_products first and use a "
        "product_id exactly as it returns it."
    )


def _match_model(p: dict, size: str | None = None) -> ProductMatch:
    return ProductMatch(
        product_id=p["product_id"],
        name=p["name"],
        garment_type=p["garment_type"],
        category=p["category"],
        price=p["price"],
        colors=p["colors"],
        short_description=short_description(p["description"]),
        total_stock=p["total_stock"],
        sizes_in_stock=search.in_stock_sizes(p),
        quantity_in_size=search.quantity_in(p, size) if size else None,
    )


def _size_or_retry(size: str | None) -> str | None:
    if size is None:
        return None
    normalized = search.normalize_size(size)
    if normalized is None:
        raise ModelRetry(f"{size!r} isn't a size the shop carries. Sizes are XS, S, M, L, XL, XXL; "
                         "tell the shopper that if they asked for another size.")
    return normalized


# ---------- product tools ----------


def find_products(
    ctx: RunContext[ShopDeps],
    query: str = "",
    category: Category | None = None,
    in_stock_size: str | None = None,
    color: ColorFamily | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    sort: SortOrder = "relevance",
    limit: int = 8,
) -> ProductSearchResult:
    """Search the catalogue with keywords and filters; returns matching products with product_id.

    Use this whenever the shopper mentions a product, kind of garment, color, sport, residential
    college, school, size, or budget. Put everything in ONE call: filters do the stock and price
    checking for you, so you don't need check_size_stock on each result.

    Args:
        query: Design/theme keywords, e.g. "Saybrook", "hockey", "vintage bulldog", "fencing hoodie".
            Can be empty when the filters say it all ("crewnecks in XL").
        category: hoodies, crewnecks (incl. sweatshirts), t-shirts, quarter-zips, jackets-fleece,
            long-sleeve, or other. Use it when the shopper names a kind of garment.
        in_stock_size: Only products with stock in this size (e.g. "M", "medium", "XL"). Use only
            when the shopper said they need that size.
        color: Main fabric color family: navy, blue, gray, white, black, red, green, yellow, pink,
            multicolor. Use it when the shopper names a color.
        max_price: Only products at or below this price in dollars.
        min_price: Only products at or above this price (for ranges like "$40-$60").
        sort: relevance (default), price_asc (cheapest first), price_desc, or name.
        limit: Maximum number of products to return (1-12).
    """
    size = _size_or_retry(in_stock_size)
    filters = search.Filters(category=category, size=size, color=color,
                             max_price=max_price, min_price=min_price)
    outcome = search.search(query, filters, sort)
    applied = {"category": category, "in_stock_size": size, "color": color,
               "min_price": min_price, "max_price": max_price}
    rename = {"size": "in_stock_size"}
    limit = max(1, min(limit, MAX_RESULTS))
    return ProductSearchResult(
        query=query,
        filters_applied={k: v for k, v in applied.items() if v is not None},
        total_before_filters=outcome.query_matches,
        removed_by_filters={rename.get(k, k): n for k, n in outcome.removed_by.items() if n},
        total_matches=len(outcome.products),
        price_min=min((p["price"] for p in outcome.products), default=None),
        price_max=max((p["price"] for p in outcome.products), default=None),
        unmatched_terms=outcome.unmatched_terms,
        matches_all_terms=outcome.matches_all_terms,
        matches=[_match_model(p, size) for p in outcome.products[:limit]],
    )


def find_alternatives(
    ctx: RunContext[ShopDeps],
    like_product_id: str | None = None,
    size: str | None = None,
    query: str | None = None,
    limit: int = 3,
) -> AlternativesResult:
    """Closest in-stock substitutes when what the shopper wants isn't available.

    Two cases:
    - A product is sold out in their size: pass like_product_id and size. Returns items in the
      same category, ranked by same main color, similar design, and similar price, that DO
      have that size in stock.
    - Nothing matches exactly (find_products gave matches_all_terms=false or unmatched_terms,
      e.g. "white t-shirt", "pink hoodie"): pass query (and size if they gave one).

    Each alternative comes with reasons. Always tell the shopper plainly that the original is
    sold out or not carried before offering these.

    Args:
        like_product_id: Exact product_id of the item they wanted.
        size: The size they need, in their words ("L", "large").
        query: What they asked for, when no product matched it exactly.
        limit: How many alternatives (1-5; 3 is usually right).
    """
    norm = _size_or_retry(size)
    like = _get_product(like_product_id) if like_product_id else None
    if like is None and not query:
        raise ModelRetry("Pass like_product_id (with size) or query.")
    if like and norm:
        qty = search.quantity_in(like, norm)
        wanted = f"{like['name']} in {norm}"
        status = f"sold out in {norm}" if qty == 0 else f"{qty} in stock in {norm}"
    elif like:
        wanted, status = like["name"], "looking for similar items"
    else:
        wanted, status = query + (f" in {norm}" if norm else ""), "no exact match in the catalogue"
    picks = search.alternatives_for(like, query or "", norm, max(1, min(limit, 5)))
    return AlternativesResult(
        wanted=wanted,
        wanted_status=status,
        size=norm,
        alternatives=[Alternative(product=_match_model(p, norm), reasons=r) for p, r in picks],
    )


def get_product_details(ctx: RunContext[ShopDeps], product_id: str) -> ProductDetails:
    """Full details for one product: description, price, colors, and exact stock for every size.

    Call this before stating a product's price, description, or stock.

    Args:
        product_id: Exact product_id from find_products (e.g. "fencing-left-chest-hoodie").
    """
    p = _get_product(product_id)
    return ProductDetails(
        product_id=p["product_id"],
        name=p["name"],
        garment_type=p["garment_type"],
        description=p["description"],
        price=p["price"],
        colors=p["colors"],
        sizes=p["sizes"],
        total_stock=p["total_stock"],
        sizes_in_stock=search.in_stock_sizes(p),
        sizes_sold_out=[s.size for s in p["sizes"] if s.quantity == 0],
    )


def check_size_stock(ctx: RunContext[ShopDeps], product_id: str, size: str) -> SizeAvailability:
    """How many of one product are in stock in one size, plus which other sizes are available.

    Call this when the shopper asks about a specific size. A status of "sold_out" means zero
    left in that size; "not_offered" means the shop doesn't carry that size at all. If it's
    sold out, call find_alternatives next.

    Args:
        product_id: Exact product_id from find_products.
        size: The size in the shopper's words, e.g. "M", "medium", "extra large", "2XL".
    """
    p = _get_product(product_id)
    normalized = search.normalize_size(size)
    match = next((s for s in p["sizes"] if s.size == normalized), None)
    return SizeAvailability(
        product_id=p["product_id"],
        name=p["name"],
        price=p["price"],
        requested_size=size,
        size=normalized,
        quantity=match.quantity if match else 0,
        status=match.status if match else "not_offered",
        other_sizes_in_stock=[s for s in search.in_stock_sizes(p) if s != normalized],
    )


# ---------- customer + page context (Problem 8) ----------


def get_customer_profile(ctx: RunContext[ShopDeps]) -> CustomerProfile | str:
    """The logged-in shopper's own account: first and last name, email, member-since date, and
    how many chat messages are saved from their past visits.

    Call this when the shopper asks what you know about them, which email their account uses,
    or how long they've been a member. Only ever describes the shopper you're talking to.
    """
    c = ctx.deps.customer
    if c is None:
        # A plain answer, not ModelRetry: retrying can't change the fact that they're a guest.
        return ("The shopper is a guest (not logged in), so there is no profile to show. "
                "Tell them they can create an account or log in. Don't call this tool again.")
    return CustomerProfile(
        first_name=c.first_name,
        last_name=c.last_name,
        email=c.email,
        member_since=c.created_at[:10],
        saved_chat_messages=memory.message_count(c.id),
    )


_PAGE_NAMES = {"/": "home", "/products": "products", "/about": "about",
               "/login": "login", "/create-account": "create-account"}


def check_page(page: PageContext) -> PageView:
    """Validate what the browser says it's showing. Only catalogue IDs survive, so nothing
    the browser sends reaches the agent's instructions as free text."""
    path = page.path.split("?")[0].rstrip("/") or "/"
    known = {p["product_id"]: p["name"] for p in search.load_catalogue()}
    view = PageView(page=_PAGE_NAMES.get(path, "other"))
    product_id = page.product_id or (path.removeprefix("/products/") if path.startswith("/products/") else None)
    if product_id in known:
        view.page, view.product_id, view.product_name = "product", product_id, known[product_id]
    if view.page == "products":
        view.visible_product_ids = [i for i in dict.fromkeys(page.visible_product_ids) if i in known]
    return view


TOOLS = [get_store_info, find_products, find_alternatives, get_product_details, check_size_stock,
         get_customer_profile]
