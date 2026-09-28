"""One catalogue search engine for both the website (search bar, filters) and the agent's tools.

Keyword matching (Problem 6-7) plus filters (Problem 9, B1): category, size in stock, main color,
max price, and sort. Because the site and the chat share this code, they can't disagree about
what matches or what's in stock.
"""

import json
import re
from dataclasses import dataclass, field

from db import SIZE_ORDER, connect
from models import Category, ColorFamily, SizeStock, SortOrder, StockStatus

LOW_STOCK = 5  # same threshold as the product page's "Only N left"

# ---------- categories and color families ----------

# The catalogue has 22 different garment_type spellings; shoppers think in these 6 (+ other).
CATEGORY_LABELS: dict[str, str] = {
    "hoodies": "Hoodies",
    "crewnecks": "Crewnecks & Sweatshirts",
    "t-shirts": "T-shirts",
    "quarter-zips": "Quarter-zips",
    "jackets-fleece": "Jackets & Fleece",
    "long-sleeve": "Long Sleeve",
    "other": "Other",
}
_CATEGORY_RULES = [  # first keyword found in garment_type wins
    ("hood", "hoodies"),
    ("quarter-zip", "quarter-zips"),
    ("jacket", "jackets-fleece"),
    ("t-shirt", "t-shirts"),
    ("long-sleeve", "long-sleeve"),
    ("crewneck", "crewnecks"),
    ("mockneck", "crewnecks"),
]

COLOR_LABELS: dict[str, str] = {
    "navy": "Navy", "blue": "Blue", "gray": "Gray", "white": "White / Cream", "black": "Black",
    "red": "Red", "green": "Green", "yellow": "Yellow / Gold", "pink": "Pink / Coral",
    "multicolor": "Multicolor",
}
_COLOR_RULES = [  # first keyword found in the main color wins ("navy blue" -> navy)
    ("navy", "navy"), ("blue", "blue"), ("gray", "gray"), ("grey", "gray"), ("charcoal", "gray"),
    ("white", "white"), ("ivory", "white"), ("cream", "white"), ("black", "black"),
    ("red", "red"), ("green", "green"), ("yellow", "yellow"), ("gold", "yellow"),
    ("coral", "pink"), ("pink", "pink"), ("multicolor", "multicolor"),
]


def category_of(garment_type: str) -> Category:
    g = garment_type.lower()
    return next((cat for kw, cat in _CATEGORY_RULES if kw in g), "other")


def color_family_of(colors: list[str]) -> ColorFamily | None:
    if not colors:
        return None
    main = colors[0].lower()
    return next((fam for kw, fam in _COLOR_RULES if kw in main), None)


def _family_of_word(word: str) -> str | None:
    return next((fam for kw, fam in _COLOR_RULES if kw == word), None)


# Price ranges for the Products-page filter: key -> (label, min inclusive, max inclusive).
# Catalogue prices are $32, $45, $58, $68, $72, $88, $98. Three ranges that match how people
# shop: tees and budget picks (30 items), everyday hoodies and crewnecks (51), and quarter-zips,
# jackets, and premium brands (21).
PRICE_BUCKETS: dict[str, tuple[str, float | None, float | None]] = {
    "under-50": ("Under $50", None, 49.99),
    "50-70": ("$50–$70", 50, 70),
    "70-plus": ("$70+", 70.01, None),
}


def price_bucket_of(price: float) -> str:
    return next(k for k, (_, lo, hi) in PRICE_BUCKETS.items()
                if (lo is None or price >= lo) and (hi is None or price <= hi))


# ---------- text matching ----------

# Rewrite common ways of saying the same garment/color into one token before matching.
_PHRASES = [
    (r"\bt[\s-]?shirts?\b|\btees?\b", " tshirt "),
    (r"\b(?:1[\s/-]?4|quarter)[\s-]?zips?\b", " quarterzip "),
    (r"\bfull[\s-]?zips?\b", " fullzip "),
    (r"\bcrew[\s-]?necks?\b", " crewneck "),
    (r"\bmock[\s-]?necks?\b", " mockneck "),
    (r"\bhooded\b|\bhoodies?\b|\bhoods?\b", " hoodie "),
    (r"\bgrey\b", " gray "),
    (r"\bsweaters?\b", " sweater "),
]
STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "do", "for", "have", "i", "in", "is", "it", "me", "my",
    "of", "on", "or", "show", "some", "that", "the", "to", "what", "with", "you", "your", "got",
    "looking", "want", "need", "something", "one", "ones", "item", "items",
}
# Words on nearly every product: they can boost a match but never create one on their own.
GENERIC = {"yale", "campus", "custom", "merch", "college", "apparel"}
# Color words only count as a match against a product's main color (first in `colors`),
# so "navy hoodie" skips gray hoodies that merely have navy lettering.
COLOR_WORDS = {
    "black", "blue", "brown", "charcoal", "coral", "cream", "gold", "gray", "green", "heather",
    "ivory", "maroon", "multicolor", "navy", "orange", "pink", "purple", "red", "royal", "tan",
    "white", "yellow",
}
# Kinds of item the shop doesn't sell. These words never match a product (a hoodie whose graphic
# shows a bulldog in a sailor hat is not a hat), so the agent hears "not carried" instead.
NOT_CARRIED = {
    "hat", "cap", "beanie", "polo", "short", "pant", "sweatpant", "jogger", "legging", "sock",
    "bag", "backpack", "tote", "mug", "cup", "bottle", "jersey", "scarf", "glove", "mitten",
    "blanket", "sticker", "flag", "dress", "skirt", "onesie",
}
_GARMENT_WORDS = {
    "hoodie", "crewneck", "tshirt", "sweatshirt", "pullover", "quarterzip", "fullzip", "jacket",
    "fleece", "shirt", "sleeve", "long", "short", "top", "zip", "kangaroo", "pocket", "drawstring",
    "chest", "left", "logo", "graphic", "lettering", "wordmark",
}
_FIELD_WEIGHTS = {"name": 3, "type": 3, "tags": 2, "colors": 2, "desc": 1}

SIZE_WORDS = {
    "xs": "XS", "extra small": "XS", "x-small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "double xl": "XXL",
    "extra extra large": "XXL",
}


def tokens(text: str) -> set[str]:
    text = text.lower()
    for pattern, repl in _PHRASES:
        text = re.sub(pattern, repl, text)
    words = re.findall(r"[a-z0-9]+", text)
    # crude singular: "hoodies" -> "hoodie", "crewnecks" -> "crewneck" (leave "dress", "bus")
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words}


def normalize_size(size: str) -> str | None:
    return SIZE_WORDS.get(size.strip().lower().rstrip("."))


# ---------- catalogue ----------


def stock_status(quantity: int) -> StockStatus:
    if quantity == 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK else "in_stock"


def load_catalogue() -> list[dict]:
    """Every product with parsed colors/tags, stock per size, category, and main color family.
    Read fresh on each call so answers always reflect the current inventory table."""
    with connect() as conn:
        products = conn.execute("SELECT * FROM catalogue").fetchall()
        stock = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    sizes: dict[str, list[SizeStock]] = {}
    for s in stock:
        sizes.setdefault(s["product_id"], []).append(
            SizeStock(size=s["size"], quantity=s["quantity"], status=stock_status(s["quantity"]))
        )
    catalogue = []
    for p in products:
        colors = json.loads(p["colors"])
        size_list = sorted(sizes.get(p["product_id"], []), key=lambda s: SIZE_ORDER.index(s.size))
        catalogue.append({
            **dict(p),
            "colors": colors,
            "search_tags": json.loads(p["search_tags"]),
            "sizes": size_list,
            "category": category_of(p["garment_type"]),
            "color_family": color_family_of(colors),
            "total_stock": sum(s.quantity for s in size_list),
        })
    return catalogue


def in_stock_sizes(product: dict) -> list[str]:
    return [s.size for s in product["sizes"] if s.quantity > 0]


def quantity_in(product: dict, size: str) -> int:
    return next((s.quantity for s in product["sizes"] if s.size == size), 0)


def _match(product: dict, q_tokens: set[str], specific: set[str]) -> tuple[set[str], int]:
    """Which specific query words this product matches, and a relevance score."""
    fields = {
        "name": tokens(product["name"]),
        "type": tokens(product["garment_type"]),
        "tags": tokens(" ".join(product["search_tags"])),
        "colors": tokens(" ".join(product["colors"])),
        "desc": tokens(product["description"]),
    }
    main_color = tokens(product["colors"][0]) if product["colors"] else set()

    def color_hit(word: str) -> bool:  # "pink" also matches a dusty-coral main color
        family = _family_of_word(word)
        return word in main_color or (family is not None and family == product["color_family"])

    hits = {
        t for t in specific - NOT_CARRIED
        if (color_hit(t) if t in COLOR_WORDS else any(t in f for f in fields.values()))
    }
    score = sum(_FIELD_WEIGHTS[k] for t in q_tokens for k, f in fields.items() if t in f)
    return hits, score


# ---------- search ----------


@dataclass
class Filters:
    category: Category | None = None
    size: str | None = None  # normalized XS..XXL: only products with stock in this size
    color: ColorFamily | None = None
    max_price: float | None = None  # inclusive
    min_price: float | None = None  # inclusive

    def _price_ok(self, price: float) -> bool:
        return ((self.min_price is None or price >= self.min_price)
                and (self.max_price is None or price <= self.max_price))

    def passes(self, p: dict, skip: str | None = None) -> bool:
        return (
            (skip == "category" or self.category is None or p["category"] == self.category)
            and (skip == "size" or self.size is None or quantity_in(p, self.size) > 0)
            and (skip == "color" or self.color is None or p["color_family"] == self.color)
            and (skip == "price" or self._price_ok(p["price"]))
        )

    def active(self) -> list[str]:
        names = [n for n in ("category", "size", "color") if getattr(self, n) is not None]
        if self.min_price is not None or self.max_price is not None:
            names.append("price")
        return names


@dataclass
class SearchOutcome:
    products: list[dict]  # matches that pass every filter, sorted
    query_matches: int  # matches for the words alone, before any filter
    removed_by: dict[str, int]  # how many word-matches each filter removed on its own
    unmatched_terms: list[str]
    matches_all_terms: bool
    category_counts: dict[str, int] = field(default_factory=dict)  # for tabs: every filter but category
    color_counts: dict[str, int] = field(default_factory=dict)  # for chips: every filter but color
    price_counts: dict[str, int] = field(default_factory=dict)  # per PRICE_BUCKETS key: every filter but price


def search(query: str = "", filters: Filters | None = None, sort: SortOrder = "relevance") -> SearchOutcome:
    filters = filters or Filters()
    q_tokens = tokens(query) - STOPWORDS
    specific = q_tokens - GENERIC
    catalogue = load_catalogue()

    scored, matched_anywhere = [], set()
    for p in catalogue:
        hits, score = _match(p, q_tokens, specific)
        matched_anywhere |= hits
        if specific and not hits:
            continue
        scored.append((len(hits), score, p))
    # Keep only products that match as many of the shopper's words as the best match does,
    # so "navy hoodie" doesn't also return every navy crewneck.
    best = max((n for n, _, _ in scored), default=0)
    word_matches = [(score, p) for n, score, p in scored if n == best]

    passing = [(score, p) for score, p in word_matches if filters.passes(p)]
    if sort == "price_asc":
        passing.sort(key=lambda x: (x[1]["price"], x[1]["name"]))
    elif sort == "price_desc":
        passing.sort(key=lambda x: (-x[1]["price"], x[1]["name"]))
    elif sort == "name":
        passing.sort(key=lambda x: x[1]["name"])
    else:  # relevance, then name
        passing.sort(key=lambda x: (-x[0], x[1]["name"]))

    # For size/color/price: products that pass every OTHER filter but fail this one, i.e. what
    # this filter alone is hiding ("3 hoodies under $60 are sold out in M"). Category is left out:
    # "not a hoodie" isn't something the shopper needs to hear about.
    removed_by = {
        name: sum(1 for _, p in word_matches if filters.passes(p, skip=name) and not filters.passes(p))
        for name in filters.active() if name != "category"
    }

    category_counts: dict[str, int] = {}
    color_counts: dict[str, int] = {}
    price_counts: dict[str, int] = {}
    for _, p in word_matches:
        if filters.passes(p, skip="category"):
            category_counts[p["category"]] = category_counts.get(p["category"], 0) + 1
        if filters.passes(p, skip="color") and p["color_family"]:
            color_counts[p["color_family"]] = color_counts.get(p["color_family"], 0) + 1
        if filters.passes(p, skip="price"):
            key = price_bucket_of(p["price"])
            price_counts[key] = price_counts.get(key, 0) + 1

    return SearchOutcome(
        products=[p for _, p in passing],
        query_matches=len(word_matches),
        removed_by=removed_by,
        unmatched_terms=sorted(specific - matched_anywhere),
        matches_all_terms=bool(word_matches) and best == len(specific),
        category_counts=category_counts,
        color_counts=color_counts,
        price_counts=price_counts,
    )


# ---------- alternatives (Problem 9, B2) ----------


def alternatives_for(like: dict | None, query: str, size: str | None,
                     limit: int = 3) -> list[tuple[dict, list[str]]]:
    """Closest in-stock substitutes, each with the reasons it was picked.

    like:  the product the shopper wanted (e.g. sold out in their size), or None
    query: what they asked for when nothing matched exactly (e.g. "white t-shirt")
    size:  normalized size they need; alternatives must have it in stock
    """
    q_tokens = tokens(query) - STOPWORDS - GENERIC - NOT_CARRIED
    if not like and not q_tokens:
        return []  # only asked for things we don't sell ("hat"): no honest substitute
    # Design overlap ignores color and garment words ("navy", "hoodie", "pullover"), which the
    # category and color checks already cover, so "similar design" means sport/college/graphic.
    not_design = GENERIC | STOPWORDS | COLOR_WORDS | _GARMENT_WORDS
    like_tags = tokens(" ".join(like["search_tags"])) - not_design if like else set()
    wanted_colors = {t for t in q_tokens if t in COLOR_WORDS}
    candidates = []
    for p in load_catalogue():
        if like and p["product_id"] == like["product_id"]:
            continue
        if size and quantity_in(p, size) == 0:
            continue
        if not size and p["total_stock"] == 0:
            continue
        reasons, score = [], 0
        if like:
            if p["category"] != like["category"]:
                continue  # an alternative to a hoodie must be a hoodie
            reasons.append(f"also {CATEGORY_LABELS[p['category']].lower()}")
            score += 3
            if p["color_family"] and p["color_family"] == like["color_family"]:
                reasons.append(f"same main color ({p['colors'][0]})")
                score += 3
            shared = like_tags & (tokens(" ".join(p["search_tags"])) - not_design)
            if shared:
                reasons.append("similar design (" + ", ".join(sorted(shared)[:3]) + ")")
                score += min(len(shared), 3)
            if abs(p["price"] - like["price"]) <= 10:
                reasons.append("similar price")
                score += 1
        else:
            hits, match_score = _match(p, q_tokens, q_tokens)
            if not hits:
                continue
            reasons.append("matches " + ", ".join(f"'{h}'" for h in sorted(hits)))
            missing = q_tokens - hits
            if missing:
                reasons.append("not " + ", ".join(f"'{m}'" for m in sorted(missing)))
            if wanted_colors and not wanted_colors & tokens(p["colors"][0] if p["colors"] else ""):
                score -= 1
            score += 5 * len(hits) + match_score
        if size:
            reasons.append(f"{quantity_in(p, size)} in stock in {size}")
        candidates.append((score, p, reasons))
    candidates.sort(key=lambda x: (-x[0], x[1]["price"], x[1]["name"]))
    return [(p, reasons) for _, p, reasons in candidates[:limit]]
