# Usability Improvements

Four improvements: two on the front end and two in the agent and backend. Each section says what we added, why it helps a Campus Customs shopper or the business, and how to see it running.

| # | Improvement | Where to see it |
|---|---|---|
| **F1** | Live search bar in the nav, with a hand-off to the assistant | Top of every page |
| **F2** | Category tabs, filters (size in stock, color, price), and sorting | `/products` |
| **B1** | Smarter search filters: one search engine for the site *and* the chat | Chat: "hoodies under $60 in M" |
| **B2** | Alternatives when a size is sold out or nothing matches exactly | Chat: "this in large?" on a sold-out size |

**Running it:** start the backend from `backend/` with `uvicorn main:app --reload --port 8000`, and the frontend from `frontend/` with `npm run dev`. Then open http://127.0.0.1:5173.

---

## F1. Live search bar (front end)

**What we added** (`frontend/src/components/SearchBar.tsx`)

- **A search box in the nav bar on every page.** As you type, a dropdown shows the top 6 matches with thumbnail, name, and price, updating live about 200 ms after you stop typing.
- **Clicking a result** opens its product page. **Enter** (or "See all 17 results for 'navy hood'") opens the Products page filtered to that search (`/products?q=navy%20hood`).
- **Keyboard support:** arrow keys, Enter, and Esc work. Clicking outside closes the dropdown.
- **The hand-off to the assistant.** When a search finds nothing ("polo"), the dropdown doesn't dead-end. It offers **"💬 Ask our assistant about 'polo'"**. One click opens the chat and asks the question for you, and the agent answers honestly with the closest things we do carry.
- **A new search replaces the chat's picks.** If the assistant had put products on the Products page, searching from the bar clears them, so your search results are the first thing you see. You don't have to close the chat's results box first.
- **Same results as the chat.** It uses the same `/api/search` engine as the agent (see B1), so "navy hood" means the same thing in the search box and in the chat.

**Why it helps the shopper:** most people who know what they want go straight to a search box, not a chatbot. They get from "navy hood…" to the product in two clicks, without scrolling 102 items or starting a conversation.

**Why it helps the business:** searchers are usually the most ready-to-buy visitors. A search that returns nothing is where a sale is usually lost, and the "ask the assistant" hand-off turns that dead end into a conversation with alternatives (B2) instead of a bounce.

**See it:** type `navy hood` in the nav search, press Enter, then type `polo` and click "Ask our assistant".

---

## F2. Categories, filters, and sorting (front end)

**What we added** (`frontend/src/pages/Products.tsx`)

- **Category tabs:** All · Hoodies · Crewnecks & Sweatshirts · T-shirts · Quarter-zips · Jackets & Fleece · Long Sleeve, each with a live count. The catalogue has **22 inconsistent `garment_type` spellings** ("pullover hoodie", "hooded sweatshirt", "short-sleeve T-shirt" vs "short-sleeve t-shirt"…). The backend maps them into these 6 groups shoppers actually think in.
- **Filters, as a single row of dropdowns** (like the Sort menu, so the bar stays on one line):
  - **Size in stock** (XS–XXL): only shows items you can actually get in your size.
  - **Color** (main fabric color), e.g. "Navy (44)", "Gray (49)", "Pink / Coral (1)". Each option shows how many items you'd get.
  - **Price:** three ranges that match how people shop: **Under $50 (30)**, tees and budget picks · **$50–$70 (51)**, everyday hoodies and crewnecks · **$70+ (21)**, quarter-zips, jackets, and premium brands. Ranges with nothing in them are disabled.
- **Sort** (at the far right): best match, price low→high, price high→low, or A–Z.
- **Feedback on what's selected:**
  - result count ("8 items")
  - removable chips for each active filter, plus "Clear all"
  - tab and color counts that update with the other filters, so you can see "Hoodies 8" before clicking
- **Friendly empty state.** Instead of a blank page: "No matches for Hoodies, Pink / Coral. Try removing a filter. Our assistant can suggest the closest things we do have." It has **Clear filters** and **Ask the assistant** buttons. The second one asks the chat "Do you have any pink hoodies?" for you.
- **Filters live in the URL** (`/products?category=hoodies&size=M&color=gray&sort=price_asc&price=50-70`). Back and refresh keep your filters, and a filtered view can be shared as a link.

**Why it helps the shopper:** 102 cards in one list is a lot to take in. Tabs and filters narrow it to the few that fit ("gray hoodies in M": 8 items), and the size filter means no falling for something that's sold out in your size.

**Why it helps the business:** too much choice makes people *less* likely to buy. A short, relevant list makes deciding easy. Filtering by size-in-stock also stops disappointment at the last step, and the empty state hands shoppers to the assistant instead of letting them leave.

**See it:** open Products, click **Hoodies**, then pick **M** under Size and **Gray** under Color. Change the sort to "Price: low to high" and pick a price range. Then visit `/products?category=hoodies&color=pink` for the empty state.

---

## B1. Smarter search filters: one engine for the site and the chat (agent + backend)

**What we added**

- **`backend/search.py`**, a single search engine. It does keyword matching (from Problems 6 and 7) plus filters: `category`, size in stock, main color family, max price, and sort. It also maps the 22 garment types into categories and each product's main color into a color family.
- **The agent's `find_products` tool now takes those filters:** `find_products(query, category, in_stock_size, color, max_price, sort)`. The prompt tells the agent to put the whole question into **one call**: "hoodies under $60 in medium" → `category="hoodies", in_stock_size="M", max_price=60`.
- **The result reports what each filter hid** (`removed_by_filters`), so the agent can be honest about near misses: "Three more navy crewnecks matched but are sold out in XL."
- **`GET /api/search`** puts the same engine behind the site's search bar (F1) and filters (F2).

**Why it helps the shopper: faster, more accurate answers.** Before, the agent searched, then checked stock item by item, then filtered in its head. Now code does the filtering and the agent just reads a short, correct list.

Measured with the same 4 questions before and after (`scripts/measure_agent.py`, 2 runs each, Portkey's cache bypassed; raw data in `output/usability_measurements.json`):

| Question | Model calls | Tool calls | Input tokens | Seconds |
|---|---|---|---|---|
| Do you have hoodies under $60 in stock in medium? | 3 → **2** | 3 → **1** | 9,920 → **8,373** | 7.6 → **4.9** |
| Any navy crewnecks in XL? | 3 → **2** | 10 → **1** | 13,110 → **8,799** | 10.2 → **5.2** |
| What's the cheapest quarter-zip you have in stock in small? | 3 → **2** | 10 → **1** | 14,212 → **8,509** | 11.4 → **6.1** |
| Show me gray t-shirts in XXL. | 2.5 → **2** | 7 → **1** | 11,022 → **9,472** | 9.5 → **5.5** |
| **Average** | 2.9 → **2** | 7.5 → **1** | 12,066 → **8,788 (−27%)** | 9.7 → **5.4 (−44%)** |

**Why it helps the business:**
- **Lower cost:** about 27% fewer tokens per filtered question, which adds up across every shopper.
- **Consistency:** the search bar, the filters, and the chat share one engine, so the website and the assistant can never disagree about what's in stock.

**Trade-offs we accepted:**
- **A wrong filter can silently hide items.** If the agent adds `in_stock_size` when the shopper didn't need that size, products disappear. The prompt only allows the size filter when the shopper says they need it, and `removed_by_filters` makes anything hidden visible to the agent.
- **A slightly longer tool description** costs a few tokens on every call. That's small next to the ~3,300 tokens saved on each filtered question.
- **Categories and color families are rules we maintain.** A new garment type (e.g. "beanie") would land in "Other" until it's added. Three products have no colors in the database, so they don't show under any color filter.

**See it:** in the chat, ask "Do you have hoodies under $60 in stock in medium?" or "Any navy crewnecks in XL?"

---

## B2. Alternatives when the exact thing isn't available (agent + backend)

**What we added**

- **A new agent tool, `find_alternatives`** (`backend/tools.py`, with the logic in `search.alternatives_for`). It covers the two dead ends shoppers hit most:
  1. **Size sold out:** `find_alternatives(like_product_id, size)` returns items in the **same category** that **have that size in stock**. They're ranked by same main color, shared design tags (college crest, sport, vintage bulldog), and similar price.
  2. **No exact match:** `find_alternatives(query, size?)` returns the closest real items, clearly labeled with what they do and don't match. Examples: "pink hoodie" → hoodies, marked *not pink*; "white t-shirt" → tees, marked *not white*.
- **Every alternative has reasons**, e.g. `["also hoodies", "same main color (navy)", "similar price", "8 in stock in L"]`. The agent quotes these instead of inventing a sales pitch.
- **Items the shop doesn't sell at all** (hats, polos, shorts, bags…) are treated as "not carried". A hoodie whose graphic shows a bulldog in a sailor hat no longer counts as a "hat". If there's no reasonable substitute (hats), the agent just says so. For a polo it offers the closest real garments, T-shirts.
- **Prompt rules** (`prompts/prompt.md` → "Offering alternatives"): give the bad news first and plainly, offer at most 3 alternatives with a short reason each, never call an alternative the thing they asked for, and show them as tappable cards. The cards usually appear in the chat. When the agent frames them as a list ("Closest hoodie alternatives"), they appear at the top of the Products page instead.

**Why it helps the shopper:** before, "Fencing hoodie in large?" got "Sorry, sold out in L", which is honest but a dead end. Now it's: "Sorry, the Fencing Left Chest Hoodie is sold out in large… here are a few navy hoodie alternatives with large in stock: Basic Hoodie Big Yale (8 left), Champion Reverse Weave Hoodie 1 (20 left), and Crew Left Chest Hoodie (8 left)." The shopper can tap one straight to its page. On the Saybrook College Crewneck page, "I need this in XXL" suggests other residential-college crest crewnecks that have XXL.

**Why it helps the business:** a sold-out size or a missing item is the moment a shopper usually leaves. Offering a close, in-stock substitute keeps them browsing and gives the sale a second chance. This site has no checkout, so we can't measure sales here. What we can show is that every dead end now ends with real, buyable options.

**Trade-offs we accepted:**
- **"Similar" is a rule, not taste.** It uses category, main color, shared tags, and price, so an alternative can occasionally be a stretch. Requiring the same category and capping it at 3 keeps it relevant.
- **Offering substitutes could feel pushy.** The prompt makes the agent state the bad news first and keep alternatives short.

**See it:** open the Fencing Left Chest Hoodie page, open the chat, and ask "Do you have this in large?" Then ask "Any pink hoodies?" and tap an alternative card.

---

## Fixes after hands-on testing

Using the site myself turned up two problems, both fixed:

1. **Search results were hidden under the chat's picks.** After the assistant put products on the Products page, a search from the bar landed *below* that box, so you had to close it first. Now a search-bar search clears the chat's picks (`SearchBar.tsx` → `clearResults()`).
2. **Price was only "under $X".** It's now three ranges (Under $50 / $50–$70 / $70+) with counts. The backend gained `min_price` in `search.Filters` and a `price=<range>` parameter on `/api/search`. The agent's `find_products` also accepts `min_price`, so "something between $40 and $60" works in the chat too.

3. **The filter buttons were busy.** Size, color, and price pills took two rows. They're now dropdowns in one row, matching the Sort menu, and each option shows its count. While switching, I found that changing filters quickly could drop earlier ones (each change started from a stale copy of the URL). Filters now build on the browser's live URL, so a tab plus three dropdown changes in a row all stick.

## How the four fit together

```
            ┌─────────── F1 search bar ──────────┐
shopper ────┤                                    ├──▶ GET /api/search ──┐
            └─────────── F2 filters/tabs ────────┘                      │
                                                                        ▼
                      "Ask the assistant" (dead ends) ──┐        B1 search.py (one engine)
                                                        ▼               ▲
            chat ──▶ /api/chat ──▶ agent ── find_products (B1) ─────────┤
                                         └─ find_alternatives (B2) ─────┘
```

All four share one engine and one category/color mapping. The site and the chat always agree, and the two front-end dead ends (a search with no results, filters with no results) hand off to the assistant, where B2 offers alternatives.
