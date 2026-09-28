"""Structured types shared by the API and the agent."""

from typing import Literal

from pydantic import BaseModel, Field

# Shopper-facing groupings (Problem 9). search.py maps the catalogue's 22 garment_type
# spellings into Category and each product's main color into ColorFamily.
Category = Literal["hoodies", "crewnecks", "t-shirts", "quarter-zips", "jackets-fleece", "long-sleeve", "other"]
ColorFamily = Literal["navy", "blue", "gray", "white", "black", "red", "green", "yellow", "pink", "multicolor"]
SizeName = Literal["XS", "S", "M", "L", "XL", "XXL"]
SortOrder = Literal["relevance", "price_asc", "price_desc", "name"]


class ProductCard(BaseModel):
    """What the site needs to draw one product card."""

    product_id: str
    name: str
    garment_type: str
    category: Category
    color_family: ColorFamily | None
    short_description: str
    price: float
    image_url: str
    total_stock: int
    sizes_in_stock: list[str] = Field(default_factory=list, description="In XS→XXL order.")


class ShopReply(BaseModel):
    """The agent's structured answer to one shopper message."""

    message: str = Field(
        description="Reply to the shopper, in plain text (no markdown), in the Campus Customs voice."
    )
    product_ids: list[str] = Field(
        default_factory=list,
        description="product_id values of catalogue items to show with the reply, best match first "
        "(up to 12). Only use IDs returned by a tool; leave empty if none apply.",
    )
    results_heading: str | None = Field(
        default=None,
        description="Set this when the shopper is searching or browsing for a kind of item, and "
        "product_ids are the search results: a short title for the results shown on the page, "
        "e.g. 'Navy hoodies' or 'Gray T-shirts under $35'. Leave null when you're answering "
        "about one or two specific products (those show as small cards in the chat instead).",
    )


# ---------- tool results (Problem 6) ----------

StockStatus = Literal["in_stock", "low_stock", "sold_out", "not_offered"]


class SizeStock(BaseModel):
    """Stock for one size of one product, straight from the inventory table."""

    size: str
    quantity: int
    status: StockStatus


class ProductMatch(BaseModel):
    """One search hit: enough to name, price, and tell apart similar items."""

    product_id: str
    name: str
    garment_type: str
    price: float
    colors: list[str] = Field(
        description="Colors that appear on this one garment: main fabric color first, then "
        "lettering/graphic colors. Not a list of color options; each product has one colorway."
    )
    short_description: str
    category: Category
    total_stock: int
    sizes_in_stock: list[str]
    quantity_in_size: int | None = Field(
        default=None, description="Stock in the size you filtered by (in_stock_size), if any."
    )


class ProductSearchResult(BaseModel):
    query: str
    filters_applied: dict[str, str | float] = Field(
        description="The filters used, e.g. {'category': 'hoodies', 'in_stock_size': 'M', 'max_price': 60}."
    )
    total_before_filters: int = Field(description="Products matching the words alone, before filters.")
    removed_by_filters: dict[str, int] = Field(
        description="How many word-matches each filter removed on its own, e.g. {'in_stock_size': 6} "
        "means 6 otherwise-matching products are sold out in that size. Mention these when relevant."
    )
    total_matches: int = Field(description="Matches after filters, before the result limit was applied.")
    price_min: float | None = Field(description="Lowest price across ALL total_matches, not just those returned.")
    price_max: float | None = Field(description="Highest price across ALL total_matches, not just those returned.")
    unmatched_terms: list[str] = Field(
        description="Search words that no product matched (e.g. 'polo' when the shop sells no polos)."
    )
    matches_all_terms: bool = Field(
        description="False when no single product matches every search word, so the results are "
        "only partial matches (e.g. 'white t-shirt' when no T-shirt is mainly white)."
    )
    matches: list[ProductMatch]


class ProductDetails(BaseModel):
    """Everything the shop knows about one product, including stock for every size."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    colors: list[str] = Field(
        description="Colors that appear on this one garment: main fabric color first, then "
        "lettering/graphic colors. Not a list of color options; each product has one colorway."
    )
    sizes: list[SizeStock]
    total_stock: int
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]


class SizeAvailability(BaseModel):
    """Answer to "do you have X in size Y?"."""

    product_id: str
    name: str
    price: float
    requested_size: str = Field(description="The size exactly as the shopper asked for it.")
    size: str | None = Field(description="Normalized shop size (XS–XXL), or None if not a size we carry.")
    quantity: int
    status: StockStatus
    other_sizes_in_stock: list[str]


class Alternative(BaseModel):
    product: ProductMatch
    reasons: list[str] = Field(description="Why this was picked, e.g. 'same main color (navy)', '8 in stock in L'.")


class AlternativesResult(BaseModel):
    """Closest in-stock substitutes when the exact item or size isn't available (Problem 9, B2)."""

    wanted: str = Field(description="What the shopper wanted, e.g. 'Fencing Left Chest Hoodie in L'.")
    wanted_status: str = Field(description="Why it isn't available, e.g. 'sold out in L' or 'no exact match'.")
    size: str | None
    alternatives: list[Alternative]


class StoreInfo(BaseModel):
    """Verified facts about the shop the agent may quote."""

    name: str
    address: str
    founded: int
    about: str
    services: list[str]
    sizes_offered: list[str]


# ---------- customer memory and page context (Problem 8) ----------


class CustomerProfile(BaseModel):
    """The logged-in shopper, as the agent is allowed to see them."""

    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Account creation date, YYYY-MM-DD.")
    saved_chat_messages: int = Field(description="Messages saved from this shopper's past chats.")


class PageContext(BaseModel):
    """Where the shopper is on the site, sent by the browser with each chat message."""

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(default=None, max_length=120, description="Set on a product page.")
    visible_product_ids: list[str] = Field(
        default_factory=list,
        max_length=12,
        description="Chat search results currently shown on the Products page, in order.",
    )


# ---------- HTTP request/response bodies for /api/chat ----------


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Only used for guests; logged-in shoppers' history is loaded from the database.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext = Field(default_factory=PageContext)


class SearchResponse(BaseModel):
    """GET /api/search: the site's search bar and Products-page filters (Problem 9)."""

    query: str
    total: int
    products: list[ProductCard]
    unmatched_terms: list[str]
    matches_all_terms: bool
    category_counts: dict[str, int] = Field(description="Result count per category, ignoring the category filter (for tabs).")
    color_counts: dict[str, int] = Field(description="Result count per color family, ignoring the color filter.")
    price_counts: dict[str, int] = Field(description="Result count per price range, ignoring the price filter.")
    category_labels: dict[str, str]
    color_labels: dict[str, str]
    price_labels: dict[str, str] = Field(description="Price range key -> label, in display order.")


class HistoryMessage(BaseModel):
    """One saved message, as the chat widget redraws it."""

    role: Literal["user", "assistant"]
    content: str
    results_heading: str | None = None
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


class ChatResponse(BaseModel):
    """What /api/chat returns to the site.

    - results_heading set  -> a search: the site shows `products` as cards on the page.
    - results_heading null -> the site shows any `products` as small cards inside the chat.
    """

    reply: str
    results_heading: str | None = None
    products: list[ProductCard] = Field(default_factory=list)
