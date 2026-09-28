"""Live app check: drives the running site, verifies answers against the database, and writes
output/app_check.html plus its screenshots in output/app_check_images/ (linked by relative path,
so the page opens with a double-click as long as the two stay side by side).

Needs both servers running (backend :8000, frontend :5173). From hw4/:
    venv/bin/python scripts/app_check.py
"""

import html
import json
import re
import sqlite3
import urllib.request
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

HW4 = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:5173"
DB = HW4 / "data" / "campus_customs.db"
OUT_HTML = HW4 / "output" / "app_check.html"
SHOTS = HW4 / "output" / "app_check_images"


def api(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.loads(res.read())


def db(sql: str, *args):
    with sqlite3.connect(DB) as conn:
        return conn.execute(sql, args).fetchall()


def ask_in_chat(page: Page, text: str) -> str:
    if page.locator(".chat-launcher").count():
        page.click(".chat-launcher")
    page.wait_for_selector(".chat-panel")
    before = page.locator(".chat-bubble.assistant:not(.typing)").count()
    page.fill(".chat-input input", text)
    page.click(".chat-input button")
    page.wait_for_function(
        "n => document.querySelectorAll('.chat-bubble.assistant:not(.typing)').length > n",
        arg=before, timeout=120_000,
    )
    page.wait_for_timeout(700)
    page.eval_on_selector(".chat-messages", "el => { el.scrollTop = el.scrollHeight }")
    # Just the reply text (not the product-card labels inside the bubble).
    return page.locator(".chat-bubble.assistant:not(.typing)").last.evaluate(
        "el => [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim()")


def shot(page: Page, name: str, **kw) -> Path:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / name
    page.screenshot(path=path, **kw)
    return path


# ---------- the checks ----------


def check_inventory(page: Page) -> dict:
    product, size = "fencing-left-chest-hoodie", "M"
    question = "How many of these do you have in medium, and how much are they?"
    page.goto(f"{BASE}/products/{product}")
    page.wait_for_selector(".stock-table")
    reply = ask_in_chat(page, question)
    path = shot(page, "inventory.png")

    (name, price), = db("SELECT name, price FROM catalogue WHERE product_id = ?", product)
    (qty,), = db("SELECT quantity FROM inventory WHERE product_id = ? AND size = ?", product, size)
    order = ["XS", "S", "M", "L", "XL", "XXL"]
    sizes = sorted(db("SELECT size, quantity FROM inventory WHERE product_id = ?", product),
                   key=lambda r: order.index(r[0]))
    price_ok = f"${price:.2f}" in reply or f"${price:.0f}" in reply
    qty_ok = re.search(rf"\b{qty}\b", reply) is not None
    return {
        "title": "1. Chat checks the inventory level of an item",
        "shot": path,
        "caption": (f"On the {name} page, a shopper asks Dan how many are in medium and what they cost. "
                    f"His answer (${price:.2f}, {qty} in M) matches the database and the page's own stock "
                    "table right next to the chat."),
        "question": question,
        "reply": reply,
        "facts": [
            ("Price in <code>catalogue</code>", f"${price:.2f}", price_ok),
            (f"Stock in size {size} in <code>inventory</code>", str(qty), qty_ok),
            ("All sizes in <code>inventory</code>", ", ".join(f"{s}={q}" for s, q in sizes), None),
        ],
        "sql": (f"SELECT price FROM catalogue WHERE product_id='{product}';  -- {price}\n"
                f"SELECT quantity FROM inventory WHERE product_id='{product}' AND size='{size}';  -- {qty}"),
        "passed": price_ok and qty_ok,
    }


def check_category_search(page: Page) -> dict:
    question = "What crewnecks do you have?"
    page.goto(BASE + "/")
    page.evaluate("sessionStorage.removeItem('cc_chat_results')")
    page.reload()
    page.wait_for_selector(".product-card img")
    reply = ask_in_chat(page, question)
    page.wait_for_selector(".chat-results .product-card img", timeout=60_000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1600)  # let the cards finish flying in from the chat
    path = shot(page, "category_search.png")

    heading = page.locator(".chat-results h2").inner_text()
    card_links = page.locator(".chat-results a.product-card").evaluate_all(
        "els => els.map(e => e.getAttribute('href').split('/').pop())")
    in_category = api("/api/search?category=crewnecks&limit=200")
    crewneck_ids = {p["product_id"] for p in in_category["products"]}
    all_crewnecks = all(i in crewneck_ids for i in card_links)
    prices = [p["price"] for p in in_category["products"]]
    lo, hi = min(prices), max(prices)
    quoted = {float(x) for x in re.findall(r"\$(\d+(?:\.\d{2})?)", reply)}
    # Any price the agent quotes must be a real crewneck price, and a single "all $X" claim is
    # only honest if every crewneck really costs X.
    prices_ok = quoted <= set(prices) and not (len(quoted) == 1 and lo != hi and "all" in reply.lower())
    # Click a chat-added card: it must still open the Problem 3 detail page.
    first = card_links[0]
    page.click(f".chat-results a.product-card[href='/products/{first}']")
    page.wait_for_selector(".stock-table")
    detail_ok = page.url.endswith(f"/products/{first}")
    return {
        "title": "2. Search result cards appear after a category question",
        "shot": path,
        "caption": (f"After the category question “{question}”, the site moves to Products and "
                    f"{len(card_links)} real crewneck cards (image, name, price, short info) land at the top "
                    "under the agent's heading, each still opening its product page."),
        "question": question,
        "reply": reply,
        "facts": [
            ("Cards put on the page", str(len(card_links)), len(card_links) > 0),
            ("Every card is really a crewneck (checked via <code>/api/search?category=crewnecks</code>)",
             "yes" if all_crewnecks else "no", all_crewnecks),
            ("Crewnecks in the catalogue", str(in_category["total"]), None),
            ("Prices quoted in the reply are real (catalogue range "
             f"${lo:.2f}–${hi:.2f})", ", ".join(f"${q:.2f}" for q in sorted(quoted)) or "none quoted", prices_ok),
            ("Clicking a chat card opens its detail page", f"/products/{first}", detail_ok),
        ],
        "sql": ("GET /api/search?category=crewnecks  -- same engine the agent's find_products uses\n"
                f"SELECT MIN(price), MAX(price) ... crewnecks  -- {lo}, {hi}"),
        "passed": len(card_links) > 0 and all_crewnecks and detail_ok and prices_ok,
    }


def check_usability_search_bar(page: Page) -> dict:
    query = "hockey"
    page.goto(BASE + "/")
    page.wait_for_selector(".product-card img")
    page.click(".search-bar input")
    page.type(".search-bar input", query, delay=70)
    page.wait_for_selector(".search-dropdown .search-result")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)
    path = shot(page, "usability_search.png", clip={"x": 0, "y": 0, "width": 1440, "height": 620})

    shown = page.locator(".search-dropdown .search-result").count()
    see_all = page.locator(".search-action").inner_text()
    engine = api(f"/api/search?q={query}")
    names_db = db("SELECT COUNT(*) FROM catalogue WHERE lower(name || ' ' || search_tags) LIKE ?", f"%{query}%")[0][0]
    total_ok = str(engine["total"]) in see_all
    page.keyboard.press("Enter")
    page.wait_for_url(f"**/products?q={query}")
    page.wait_for_selector(".product-grid .product-card")
    page.wait_for_load_state("networkidle")
    page.wait_for_function(  # wait until the grid matches the page's own "N items" label
        "() => { const m = document.querySelector('.section-head .muted');"
        " return m && parseInt(m.textContent) === document.querySelectorAll('.product-grid .product-card').length }",
        timeout=15_000,
    )
    grid = page.locator(".product-grid .product-card").count()
    return {
        "title": "3. Usability feature (Problem 9, F1): live search bar",
        "shot": path,
        "caption": (f"Problem 9's live search bar: typing “{query}” shows matching products with photos "
                    f"and prices as you type, and its {engine['total']} results match the database."),
        "question": f"(typed in the search bar) {query}",
        "reply": f"Dropdown: {shown} previews + “{see_all.strip()}”",
        "facts": [
            ("Results the search engine reports", str(engine["total"]), None),
            ("“See all” count matches the engine", see_all.strip(), total_ok),
            ("Products whose name or tags contain “hockey” (SQL)", str(names_db), engine["total"] == names_db),
            ("Enter → Products grid shows", f"{grid} cards", grid == engine["total"]),
        ],
        "sql": f"SELECT COUNT(*) FROM catalogue WHERE lower(name || search_tags) LIKE '%{query}%';  -- {names_db}",
        "passed": total_ok and grid == engine["total"],
    }


# ---------- HTML ----------

CSS = """
:root { --blue:#00356b; --deep:#001a36; --soft:#eef3fa; --gray:#63666a; --line:#dcdcd8; --ok:#2e7d32; --bad:#b3261e; }
* { box-sizing:border-box }
body { margin:0; font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; color:#1b1f24; background:#f6f6f4 }
header { background:linear-gradient(160deg,var(--blue),var(--deep)); color:#fff; padding:36px 24px 28px }
header .inner, main, footer { max-width:1000px; margin:0 auto }
header h1 { font-family:Georgia,serif; margin:0 0 6px; font-size:2rem } header p { margin:0; opacity:.85 }
main { padding:28px 24px 48px }
.summary { width:100%; border-collapse:collapse; background:#fff; border-radius:12px; overflow:hidden;
           box-shadow:0 1px 3px rgba(0,0,0,.08); margin-bottom:32px }
.summary td { padding:12px 16px; border-bottom:1px solid var(--line) } .summary td:last-child { text-align:right }
.summary a { color:var(--blue); text-decoration:none; font-weight:600 }
.badge { font-weight:700; font-size:12px; padding:3px 10px; border-radius:999px; color:#fff }
.pass { background:var(--ok) } .fail { background:var(--bad) } .info { background:var(--gray) }
section { background:#fff; border-radius:14px; padding:24px 26px; margin-bottom:28px; box-shadow:0 1px 3px rgba(0,0,0,.08) }
h2 { font-family:Georgia,serif; color:var(--blue); margin:0 0 14px; font-size:1.45rem }
figure { margin:0 } figure img { width:100%; border:1px solid var(--line); border-radius:10px; display:block }
figcaption { margin-top:12px; font-size:1.02rem }
details { margin-top:14px; color:#333 } details summary { cursor:pointer; color:var(--blue); font-weight:600 }
.qa { background:var(--soft); border-radius:10px; padding:12px 16px; margin:12px 0; font-size:.95rem }
table.facts { width:100%; border-collapse:collapse; font-size:.95rem }
table.facts td { padding:7px 10px; border-bottom:1px solid var(--line); vertical-align:top }
table.facts td:last-child { width:70px; text-align:right }
code { background:var(--soft); padding:1px 5px; border-radius:4px; font-size:.9em }
footer { color:var(--gray); font-size:13px; padding:0 24px 40px }
"""


def esc(s) -> str:
    return html.escape(str(s))


def badge(ok) -> str:
    if ok is None:
        return '<span class="badge info">info</span>'
    return f'<span class="badge {"pass" if ok else "fail"}">{"PASS" if ok else "FAIL"}</span>'


def check_html(i: int, c: dict) -> str:
    rel = f"app_check_images/{c['shot'].name}"
    facts = "".join(f"<tr><td>{label}</td><td><b>{esc(value)}</b></td><td>{badge(ok)}</td></tr>"
                    for label, value, ok in c["facts"])
    return f"""
<section id="check-{i}">
  <h2>{esc(c['title'])} {badge(c['passed'])}</h2>
  <figure>
    <img src="{rel}" alt="{esc(c['title'])}">
    <figcaption>{esc(c['caption'])}</figcaption>
  </figure>
  <details>
    <summary>Evidence: what was asked, what the agent said, and the database check</summary>
    <div class="qa"><b>Asked:</b> {esc(c['question'])}<br><b>Answer:</b> {esc(c['reply'])}</div>
    <table class="facts">{facts}</table>
    <p><code>{esc(c['sql'])}</code></p>
  </details>
</section>"""


def build_html(checks: list[dict]) -> str:
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    summary = "".join(
        f'<tr><td><a href="#check-{i}">{esc(c["title"])}</a></td><td>{badge(c["passed"])}</td></tr>'
        for i, c in enumerate(checks, 1)
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campus Customs · App Check</title><style>{CSS}</style></head>
<body>
<header><div class="inner">
<h1>Campus Customs App Check</h1>
<p>Tested on the live site (React + Vite frontend, FastAPI + PydanticAI backend) on {esc(now)}.
Every price and stock number was checked against <code style="background:rgba(255,255,255,.15);color:#fff">campus_customs.db</code>.</p>
</div></header>
<main>
<table class="summary">{summary}</table>
{''.join(check_html(i, c) for i, c in enumerate(checks, 1))}
</main>
<footer>Regenerate with <code>venv/bin/python scripts/app_check.py</code> from <code>hw4/</code> while both servers run.
Screenshots live in <code>output/app_check_images/</code> next to this file.</footer>
</body></html>"""


def main() -> None:
    health = api("/api/health")
    assert health.get("agent_loaded"), "agent not loaded: is PORTKEY_API_KEY set?"
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        checks = [check_inventory(page), check_category_search(page), check_usability_search_bar(page)]
        browser.close()
    OUT_HTML.write_text(build_html(checks))
    for c in checks:
        print(("PASS " if c["passed"] else "FAIL ") + c["title"])
    print(f"wrote {OUT_HTML.relative_to(HW4)} + {len(list(SHOTS.glob('*.png')))} images in "
          f"{SHOTS.relative_to(HW4)}/")


if __name__ == "__main__":
    main()
