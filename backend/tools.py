"""Tools the shop agent can call.

Every price, color, size and stock answer comes from these functions, which
read the catalogue and inventory tables. The connection is opened read-only
and only those two tables are queried, so the agent can never change data or
see the users table.
"""

import json
import re
import sqlite3
from pathlib import Path

from pydantic_ai import RunContext

from models import (MAX_RESULTS, ProductDetail, ProductSummary, Recommendation, ShopDeps, SizeStock,
                    StockCheck, TaggedProduct)
from tagging import BRAND_PREFIXES, CATEGORIES, HOUSE_BRAND, STYLES, is_in_season, load_tags, seasons_now

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]

# Shoppers' words for a garment -> substrings found in catalogue.garment_type.
GARMENT_SYNONYMS: dict[str, list[str]] = {
    "hoodie": ["hoodie", "hooded"],
    "hooded": ["hoodie", "hooded"],
    "sweatshirt": ["sweatshirt", "crewneck", "hoodie", "hooded", "quarter-zip", "mockneck"],
    "crewneck": ["crewneck"],
    "crew": ["crewneck"],
    "t-shirt": ["t-shirt"],
    "tshirt": ["t-shirt"],
    "tee": ["t-shirt"],
    "shirt": ["t-shirt", "shirt"],
    "quarter-zip": ["quarter-zip"],
    "1/4 zip": ["quarter-zip"],
    "quarter zip": ["quarter-zip"],
    "jacket": ["jacket"],
    "fleece": ["fleece"],
    "long-sleeve": ["long-sleeve"],
    "long sleeve": ["long-sleeve"],
    "mockneck": ["mockneck"],
}

STOP_WORDS = {"a", "an", "the", "and", "or", "for", "with", "in", "of", "do", "you",
              "have", "any", "some", "i", "want", "need", "show", "me", "is", "are"}


def _connect(deps: ShopDeps) -> sqlite3.Connection:
    uri = f"{Path(deps.db_path).resolve().as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _normalize_size(size: str) -> str:
    s = size.strip().upper().replace("-", "").replace(" ", "")
    aliases = {"XSMALL": "XS", "EXTRASMALL": "XS", "SMALL": "S", "MEDIUM": "M", "MED": "M",
               "LARGE": "L", "XLARGE": "XL", "EXTRALARGE": "XL", "2XL": "XXL", "XXLARGE": "XXL"}
    return aliases.get(s, s)


def _keyword_in(word: str, haystack: str) -> bool:
    """Match a search word, treating plurals as singular ("hoodies" finds "Hoodie").

    Problem 11 app check found this: the agent sometimes searched query="hoodies", which
    matched no product names, so "What hoodies do you have?" came back empty.
    """
    if word in haystack:
        return True
    if len(word) > 3 and word.endswith("es") and word[:-2] in haystack:
        return True
    return len(word) > 2 and word.endswith("s") and word[:-1] in haystack


def _inventory(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    stock = [SizeStock(size=r["size"], quantity=r["quantity"]) for r in rows]
    return sorted(stock, key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99)


def load_product(conn: sqlite3.Connection, product_id: str) -> ProductDetail | None:
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    if row is None:
        return None
    inventory = _inventory(conn, product_id)
    return ProductDetail(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        search_tags=json.loads(row["search_tags"]),
        price=row["price"],
        image_url=f"/media/{row['image_file_path']}",
        inventory=inventory,
        total_stock=sum(s.quantity for s in inventory),
    )


def load_products(deps: ShopDeps, product_ids: list[str]) -> list[ProductDetail]:
    """Used by the API (not the agent) to turn the agent's chosen ids into product cards."""
    with _connect(deps) as conn:
        found = (load_product(conn, pid) for pid in dict.fromkeys(product_ids))
        return [p for p in found if p is not None]


# ---------- Agent tools ----------

def search_products(
    ctx: RunContext[ShopDeps],
    query: str | None = None,
    garment_type: str | None = None,
    color: str | None = None,
    size: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    in_stock_only: bool = False,
    limit: int = MAX_RESULTS,
) -> list[ProductSummary]:
    """Search the Campus Customs catalogue.

    Args:
        query: Free-text keywords, e.g. "hockey", "Harvard Yale game", "bulldog", "Branford".
            Matched against product name, description, search tags and garment type.
        garment_type: Kind of clothing, e.g. "hoodie", "t-shirt", "crewneck", "quarter-zip", "jacket".
        color: A color the product should include, e.g. "navy", "gray", "white".
        size: Only return products that have this size in stock (XS, S, M, L, XL, XXL).
        max_price: Highest price in US dollars.
        min_price: Lowest price in US dollars.
        in_stock_only: If true, skip products that are sold out in every size.
        limit: Maximum number of results (1-5).
    """
    limit = max(1, min(limit, MAX_RESULTS))  # Problem 12: results are capped at 5
    wanted_size = _normalize_size(size) if size else None
    type_terms: list[str] = []
    if garment_type:
        g = garment_type.lower().strip().rstrip("s")
        type_terms = GARMENT_SYNONYMS.get(g, GARMENT_SYNONYMS.get(garment_type.lower().strip(), [g]))
    keywords = [w for w in re.findall(r"[a-z0-9/]+", (query or "").lower()) if w not in STOP_WORDS]

    results: list[tuple[int, ProductSummary]] = []
    with _connect(ctx.deps) as conn:
        for row in conn.execute("SELECT * FROM catalogue"):
            gtype = row["garment_type"].lower()
            colors = json.loads(row["colors"])
            if type_terms and not any(t in gtype for t in type_terms):
                continue
            if color and not any(color.lower() in c.lower() for c in colors):
                continue
            if max_price is not None and row["price"] > max_price:
                continue
            if min_price is not None and row["price"] < min_price:
                continue

            haystack = " ".join(
                [row["name"], row["description"], gtype, " ".join(colors),
                 " ".join(json.loads(row["search_tags"]))]
            ).lower()
            score = sum(1 for k in keywords if _keyword_in(k, haystack))
            if keywords and score == 0:
                continue

            inventory = _inventory(conn, row["product_id"])
            in_stock_sizes = [s.size for s in inventory if s.quantity > 0]
            if wanted_size and wanted_size not in in_stock_sizes:
                continue
            if in_stock_only and not in_stock_sizes:
                continue

            results.append((score, ProductSummary(
                product_id=row["product_id"],
                name=row["name"],
                garment_type=row["garment_type"],
                price=row["price"],
                colors=colors,
                sizes_in_stock=in_stock_sizes,
                total_stock=sum(s.quantity for s in inventory),
            )))

    results.sort(key=lambda r: (-r[0], r[1].name))
    return [summary for _, summary in results[:limit]]


def get_product_details(ctx: RunContext[ShopDeps], product_id: str) -> ProductDetail | str:
    """Look up one product's description, price, colors and stock for every size.

    Use this for any question about a specific product's description or price, or about
    which sizes are available. `sold_out_sizes` lists every size with 0 left.

    Args:
        product_id: The product_id from a search result, e.g. "basic-hoodie-big-yale".
    """
    with _connect(ctx.deps) as conn:
        product = load_product(conn, product_id)
    return product or f"No product found with product_id '{product_id}'."


def check_stock(ctx: RunContext[ShopDeps], product_id: str, size: str) -> StockCheck | str:
    """Check how many of one product are in stock in one size, plus its price.

    `status` is "sold out" when quantity is 0, "low stock" when 5 or fewer are left.

    Args:
        product_id: The product_id from a search result.
        size: XS, S, M, L, XL or XXL (words like "medium" or "extra large" also work).
    """
    wanted = _normalize_size(size)
    with _connect(ctx.deps) as conn:
        product = load_product(conn, product_id)
    if product is None:
        return f"No product found with product_id '{product_id}'."
    by_size = {s.size: s.quantity for s in product.inventory}
    if wanted not in by_size:
        return f"{product.name} does not come in size '{size}'. Sizes offered: {', '.join(by_size)}."
    size_row = next(s for s in product.inventory if s.size == wanted)
    return StockCheck(
        product_id=product.product_id,
        name=product.name,
        price=product.price,
        size=wanted,
        quantity=size_row.quantity,
        in_stock=size_row.quantity > 0,
        status=size_row.status,
        other_sizes_in_stock=[s for s, q in by_size.items() if q > 0 and s != wanted],
    )


def _match(value: str | None, options: list[str]) -> str | None:
    """Loose match of the agent's word to one of our tag values ("formal" -> "Formal")."""
    if not value:
        return None
    v = value.lower().strip()
    return next((o for o in options if v in o.lower() or o.lower().rstrip("s") in v), value)


def browse_catalogue(
    ctx: RunContext[ShopDeps],
    category: str | None = None,
    brand: str | None = None,
    style: str | None = None,
    color: str | None = None,
    size: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    in_season_now: bool = False,
    limit: int = MAX_RESULTS,
) -> list[TaggedProduct] | str:
    """Filter the catalogue by the shop's metadata tags, with live stock (Problem 9).

    Use this for style, brand, category or seasonal questions, e.g. "something formal for an
    interview", "do you carry Champion?", "what's in season?", "quarter-zips under $80 in M".
    Only items in stock (in `size`, if given) are returned.

    Args:
        category: One of: Hoodies, Crewnecks & sweatshirts, T-shirts, Quarter-zips,
            Jackets & fleece, Long sleeves.
        brand: Campus Customs, Champion, Brooks Brothers, Under Armour, District or Hype and Vice.
        style: "Casual" or "Formal" (formal = quarter-zips, fleece and other jackets, premium pieces).
        color: A color, e.g. "navy", "gray", "white", "red".
        size: Only items in stock in this size (XS, S, M, L, XL, XXL).
        max_price: Highest price in US dollars.
        min_price: Lowest price in US dollars.
        in_season_now: Only items in today's featured seasons (see `seasons` on each result).
        limit: Maximum number of results (1-5).
    """
    limit = max(1, min(limit, MAX_RESULTS))  # Problem 12: results are capped at 5
    brands = [*BRAND_PREFIXES.values(), HOUSE_BRAND]
    want_category, want_brand, want_style = (
        _match(category, CATEGORIES), _match(brand, brands), _match(style, STYLES))
    wanted_size = _normalize_size(size) if size else None
    results: list[TaggedProduct] = []
    with _connect(ctx.deps) as conn:
        tags = load_tags(conn)
        for row in conn.execute("SELECT * FROM catalogue ORDER BY name"):
            t = tags[row["product_id"]]
            colors = json.loads(row["colors"])
            if want_category and t["category"] != want_category:
                continue
            if want_brand and t["brand"] != want_brand:
                continue
            if want_style and t["style"] != want_style:
                continue
            if color and not any(color.lower() in c.lower() for c in colors + t["color_groups"]):
                continue
            if max_price is not None and row["price"] > max_price:
                continue
            if min_price is not None and row["price"] < min_price:
                continue
            if in_season_now and not is_in_season(t["seasons"]):
                continue
            inventory = _inventory(conn, row["product_id"])
            in_stock = [s.size for s in inventory if s.quantity > 0]
            if not in_stock or (wanted_size and wanted_size not in in_stock):
                continue
            results.append(TaggedProduct(
                product_id=row["product_id"], name=row["name"], garment_type=row["garment_type"],
                price=row["price"], colors=colors, sizes_in_stock=in_stock,
                total_stock=sum(s.quantity for s in inventory), category=t["category"],
                brand=t["brand"], style=t["style"], seasons=t["seasons"],
                in_season=is_in_season(t["seasons"]),
            ))
            if len(results) >= limit:
                break
    if not results:
        return ("No in-stock items match those filters. Seasons featured today: "
                f"{', '.join(seasons_now())}. Try fewer filters.")
    return results


def recommend_for_me(ctx: RunContext[ShopDeps], limit: int = MAX_RESULTS) -> list[Recommendation] | str:
    """Tailored picks for the logged-in shopper (Problem 9), from their order history, the
    products they viewed and what the chat showed them. Every pick is in stock in their usual
    size (when known) and comes with a `reason` to mention. Only works for logged-in shoppers.

    Use this for "what would you recommend for me?", "anything new I'd like?", "suggest
    something for me".

    Args:
        limit: Maximum number of picks (1-5).
    """
    if ctx.deps.customer is None:
        return "The shopper is a guest, so there is no profile. Ask what they like, or suggest they log in."
    from customer_profile import recommend  # imported here to keep the tools module light

    with _connect(ctx.deps) as conn:
        profile, picks = recommend(conn, ctx.deps.customer.user_id, max(1, min(limit, MAX_RESULTS)))
    if not picks:
        return f"No in-stock picks right now. Profile: {profile.summary()}"
    return picks


SHOP_TOOLS = [search_products, get_product_details, check_stock, browse_catalogue, recommend_for_me]
