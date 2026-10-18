"""Product metadata tagging (Problem 9, Backend 1).

Every product gets tags the website filters and the agent tool use:
  category     - plain-language shop section (Hoodies, T-shirts, Quarter-zips, ...)
  brand        - Champion, Brooks Brothers, Under Armour, District, Hype and Vice, or Campus Customs
  style        - "Casual" or "Formal" (powers the style toggle)
  color_groups - simple colors for filtering ("navy blue" and "navy" are both Navy)
  seasons      - "Fall & winter", "Spring & summer", "Game day"

Tags are worked out from the catalogue (name, garment type, colors, search tags) by the rules
below and saved in the product_tags table every time the backend starts, so new or changed
products are tagged automatically. Which seasons are "in season now" depends on today's date.
"""

import json
import re
import sqlite3
from datetime import date

CATEGORIES = ["Hoodies", "Crewnecks & sweatshirts", "T-shirts", "Quarter-zips",
              "Jackets & fleece", "Long sleeves"]
STYLES = ["Casual", "Formal"]
SEASONS = ["Fall & winter", "Spring & summer", "Game day"]

BRAND_PREFIXES = {
    "champion-": "Champion",
    "brooks-brothers-": "Brooks Brothers",
    "ua-": "Under Armour",
    "district-": "District",
    "hype-and-vice-": "Hype and Vice",
}
HOUSE_BRAND = "Campus Customs"

COLOR_GROUPS = [  # first matching word wins
    ("navy", "Navy"), ("charcoal", "Gray"), ("gray", "Gray"), ("grey", "Gray"),
    ("white", "White & cream"), ("cream", "White & cream"), ("ivory", "White & cream"),
    ("black", "Black"), ("red", "Red & pink"), ("coral", "Red & pink"), ("pink", "Red & pink"),
    ("blue", "Blue"), ("yellow", "Yellow & gold"), ("gold", "Yellow & gold"),
    ("green", "Green"), ("multicolor", "Multicolor"),
]

FORMAL_WORDS = ("premium", "mockneck", "bomber", "brooks brothers", "dress")
GAME_DAY_WORDS = ("the game", "harvard", "boola")


def category_for(garment_type: str) -> str:
    g = garment_type.lower()
    if "quarter-zip" in g:
        return "Quarter-zips"
    if "hood" in g:
        return "Hoodies"
    if "jacket" in g or "fleece" in g:
        return "Jackets & fleece"
    if "t-shirt" in g:
        return "T-shirts"
    if "long-sleeve" in g:
        return "Long sleeves"
    return "Crewnecks & sweatshirts"


def brand_for(product_id: str) -> str:
    return next((b for prefix, b in BRAND_PREFIXES.items() if product_id.startswith(prefix)), HOUSE_BRAND)


def color_groups_for(colors: list[str]) -> list[str]:
    groups: list[str] = []
    for c in colors:
        group = next((g for word, g in COLOR_GROUPS if word in c.lower()), None)
        if group and group not in groups:
            groups.append(group)
    return groups


def tag_product(row: sqlite3.Row | dict) -> dict:
    """Work out one product's tags from its catalogue row."""
    product_id = row["product_id"]
    category = category_for(row["garment_type"])
    brand = brand_for(product_id)
    tags = json.loads(row["search_tags"]) if isinstance(row["search_tags"], str) else row["search_tags"]
    text = " ".join([row["name"], row["garment_type"], row["description"], *tags]).lower()

    formal = (category in ("Quarter-zips", "Jackets & fleece")
              or brand == "Brooks Brothers"
              or any(re.search(rf"\b{w}\b", text) for w in FORMAL_WORDS))
    seasons = ["Spring & summer"] if category == "T-shirts" else ["Fall & winter"]
    if any(w in text for w in GAME_DAY_WORDS):
        seasons.append("Game day")

    colors = json.loads(row["colors"]) if isinstance(row["colors"], str) else row["colors"]
    return {
        "product_id": product_id,
        "category": category,
        "brand": brand,
        "style": "Formal" if formal else "Casual",
        "color_groups": color_groups_for(colors),
        "seasons": seasons,
    }


def seasons_now(today: date | None = None) -> list[str]:
    """Seasons whose products are featured today. Sept to Feb is fall and winter, March to Aug
    is spring and summer, and October and November (before and during the Harvard-Yale game)
    are also game day."""
    month = (today or date.today()).month
    now = ["Fall & winter"] if month in (9, 10, 11, 12, 1, 2) else ["Spring & summer"]
    if month in (10, 11):
        now.append("Game day")
    return now


def is_in_season(seasons: list[str], today: date | None = None) -> bool:
    return any(s in seasons_now(today) for s in seasons)


def init_tags_table(conn: sqlite3.Connection) -> int:
    """Create product_tags if needed and (re)tag every product. Returns the number tagged."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS product_tags (
            product_id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            brand TEXT NOT NULL,
            style TEXT NOT NULL,
            color_groups TEXT NOT NULL,
            seasons TEXT NOT NULL,
            tagged_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES catalogue(product_id)
        );
        """
    )
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM catalogue").fetchall()
    tagged = [tag_product(r) for r in rows]
    conn.executemany(
        "INSERT INTO product_tags (product_id, category, brand, style, color_groups, seasons, tagged_at) "
        "VALUES (:product_id, :category, :brand, :style, :color_groups, :seasons, datetime('now')) "
        "ON CONFLICT(product_id) DO UPDATE SET category = excluded.category, brand = excluded.brand, "
        "style = excluded.style, color_groups = excluded.color_groups, seasons = excluded.seasons, "
        "tagged_at = excluded.tagged_at",
        [{**t, "color_groups": json.dumps(t["color_groups"]), "seasons": json.dumps(t["seasons"])} for t in tagged],
    )
    conn.execute("DELETE FROM product_tags WHERE product_id NOT IN (SELECT product_id FROM catalogue)")
    return len(tagged)


def load_tags(conn: sqlite3.Connection) -> dict[str, dict]:
    """Tags for every product, from product_tags (or worked out on the spot if the table is missing,
    for example on a read-only connection before the backend has started once)."""
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM product_tags").fetchall()
        if rows:
            return {r["product_id"]: {"product_id": r["product_id"], "category": r["category"],
                                      "brand": r["brand"], "style": r["style"],
                                      "color_groups": json.loads(r["color_groups"]),
                                      "seasons": json.loads(r["seasons"])} for r in rows}
    except sqlite3.OperationalError:
        pass
    return {r["product_id"]: tag_product(r) for r in conn.execute("SELECT * FROM catalogue")}
