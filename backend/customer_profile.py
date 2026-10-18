"""Customer profile and tailored recommendations (Problem 9, Backend 2).

The profile is built from what Campus Customs already knows about a logged-in shopper:
  - order history     (orders + order_items)   weight 3 per item bought
  - products viewed   (product_views)          weight 1 per view
  - products the chat showed them (chat_messages.products_json)   weight 0.5

From those it works out their usual size and the categories, styles, brands and colors they
like, then scores every in-stock product against those preferences. This is the in-house
customer record a CRM would normally hold. An outside CRM or distributor system could be added
later as another source in build_profile(); none exists for Campus Customs today.
"""

import json
import sqlite3
from collections import Counter

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from auth import current_user_id
from db import get_db
from models import Recommendation
from tagging import is_in_season, load_tags

router = APIRouter(prefix="/api")

WEIGHT_ORDER, WEIGHT_VIEW, WEIGHT_CHAT = 3.0, 1.0, 0.5
MAX_RECOMMENDATIONS = 8


class OrderLine(BaseModel):
    product_id: str
    name: str
    size: str
    quantity: int
    unit_price: float


class PastOrder(BaseModel):
    order_id: int
    created_at: str
    total: float
    items: list[OrderLine]


class CustomerProfile(BaseModel):
    user_id: int
    usual_size: str | None = None
    favorite_categories: list[str] = []
    favorite_styles: list[str] = []
    favorite_brands: list[str] = []
    favorite_colors: list[str] = []
    orders: list[PastOrder] = []
    products_viewed: int = 0
    signals: int = 0  # how many orders, views and chat cards the profile is based on

    def summary(self) -> str:
        """One line for the agent's instructions."""
        if not self.signals:
            return "No shopping history yet."
        parts = []
        if self.usual_size:
            parts.append(f"usual size {self.usual_size}")
        for label, values in (("likes", self.favorite_categories), ("style", self.favorite_styles),
                              ("colors", self.favorite_colors), ("brands", self.favorite_brands)):
            if values:
                parts.append(f"{label}: {', '.join(values[:3])}")
        parts.append(f"{len(self.orders)} past order(s)")
        return "; ".join(parts) + "."


def _chat_card_ids(conn: sqlite3.Connection, user_id: int) -> list[str]:
    ids: list[str] = []
    for r in conn.execute("SELECT products_json FROM chat_messages WHERE user_id = ? AND role = 'assistant' "
                          "ORDER BY id DESC LIMIT 40", (user_id,)):
        try:
            ids += [p["product_id"] for p in json.loads(r["products_json"] or "[]") if isinstance(p, dict)]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    return ids


def _safe(conn: sqlite3.Connection, sql: str, args: tuple) -> list[sqlite3.Row]:
    try:
        return conn.execute(sql, args).fetchall()
    except sqlite3.OperationalError:  # table not created yet
        return []


def build_profile(conn: sqlite3.Connection, user_id: int) -> tuple[CustomerProfile, Counter, set[str]]:
    """Returns the profile, the weighted interest in each product, and the ids already bought."""
    conn.row_factory = sqlite3.Row
    tags = load_tags(conn)
    interest: Counter = Counter()
    sizes: Counter = Counter()
    bought: set[str] = set()

    order_rows = _safe(conn, "SELECT o.id, o.created_at, o.total, oi.product_id, oi.size, oi.quantity, "
                             "oi.unit_price, c.name FROM orders o JOIN order_items oi ON oi.order_id = o.id "
                             "JOIN catalogue c ON c.product_id = oi.product_id WHERE o.user_id = ? "
                             "ORDER BY o.id DESC", (user_id,))
    orders: dict[int, PastOrder] = {}
    for r in order_rows:
        interest[r["product_id"]] += WEIGHT_ORDER * r["quantity"]
        sizes[r["size"]] += r["quantity"]
        bought.add(r["product_id"])
        order = orders.setdefault(r["id"], PastOrder(order_id=r["id"], created_at=r["created_at"],
                                                     total=r["total"], items=[]))
        order.items.append(OrderLine(product_id=r["product_id"], name=r["name"], size=r["size"],
                                     quantity=r["quantity"], unit_price=r["unit_price"]))

    views = _safe(conn, "SELECT product_id FROM product_views WHERE user_id = ?", (user_id,))
    for r in views:
        interest[r["product_id"]] += WEIGHT_VIEW
    for pid in _chat_card_ids(conn, user_id):
        interest[pid] += WEIGHT_CHAT

    likes = {k: Counter() for k in ("category", "style", "brand", "color")}
    for pid, weight in interest.items():
        t = tags.get(pid)
        if not t:
            continue
        likes["category"][t["category"]] += weight
        likes["style"][t["style"]] += weight
        likes["brand"][t["brand"]] += weight
        for c in t["color_groups"]:
            likes["color"][c] += weight

    def top(counter: Counter, n: int = 3) -> list[str]:
        return [k for k, _ in counter.most_common(n)]

    profile = CustomerProfile(
        user_id=user_id,
        usual_size=sizes.most_common(1)[0][0] if sizes else None,
        favorite_categories=top(likes["category"]),
        favorite_styles=top(likes["style"], 1),
        favorite_brands=[b for b in top(likes["brand"]) if b != "Campus Customs"] or top(likes["brand"], 1),
        favorite_colors=top(likes["color"]),
        orders=list(orders.values()),
        products_viewed=len(views),
        signals=len(order_rows) + len(views) + int(sum(1 for _ in _chat_card_ids(conn, user_id))),
    )
    return profile, interest, bought


def recommend(conn: sqlite3.Connection, user_id: int, limit: int = MAX_RECOMMENDATIONS) -> tuple[CustomerProfile, list[Recommendation]]:
    """Score every in-stock product against the shopper's profile and return the best picks."""
    profile, interest, bought = build_profile(conn, user_id)
    tags = load_tags(conn)
    total = sum(interest.values()) or 1.0
    shares = {k: Counter() for k in ("category", "style", "brand", "color")}
    for pid, w in interest.items():
        t = tags.get(pid)
        if t:
            shares["category"][t["category"]] += w / total
            shares["style"][t["style"]] += w / total
            shares["brand"][t["brand"]] += w / total
            for c in t["color_groups"]:
                shares["color"][c] += w / total

    stock: dict[str, list[tuple[str, int]]] = {}
    for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
        stock.setdefault(r["product_id"], []).append((r["size"], r["quantity"]))

    picks: list[Recommendation] = []
    for row in conn.execute("SELECT * FROM catalogue"):
        pid, t = row["product_id"], tags.get(row["product_id"])
        in_stock = [s for s, q in stock.get(pid, []) if q > 0]
        if not t or pid in bought or not in_stock:
            continue
        if profile.usual_size and profile.usual_size not in in_stock:
            continue
        parts = {
            "category": 2.0 * shares["category"][t["category"]],
            "style": 1.5 * shares["style"][t["style"]],
            "brand": 0.5 * shares["brand"][t["brand"]] if t["brand"] != "Campus Customs" else 0.0,
            "color": 1.0 * max((shares["color"][c] for c in t["color_groups"]), default=0.0),
        }
        in_season = is_in_season(t["seasons"])
        score = sum(parts.values()) + (0.3 if in_season else 0.0) - 0.4 * min(interest[pid], 3) / 3
        best = max(parts, key=parts.get)
        if parts[best] <= 0:
            reason = "In season now" if in_season else "Popular pick"
        else:
            reason = {"category": f"Because you like {t['category']}",
                      "style": f"Matches your {t['style']} style",
                      "brand": f"More from {t['brand']}",
                      "color": "In colors you like"}[best]
        if profile.usual_size:
            reason += f" · in your size {profile.usual_size}"
        elif in_season and "In season" not in reason:
            reason += " · in season"
        picks.append(Recommendation(
            product_id=pid, name=row["name"], garment_type=row["garment_type"], price=row["price"],
            colors=json.loads(row["colors"]), sizes_in_stock=in_stock,
            total_stock=sum(q for _, q in stock.get(pid, [])), category=t["category"], brand=t["brand"],
            style=t["style"], seasons=t["seasons"], in_season=in_season, reason=reason,
            score=round(score, 3), description=row["description"],
            image_url=f"/media/{row['image_file_path']}",
        ))
    picks.sort(key=lambda p: (-p.score, p.name))
    # Keep the row varied: at most 3 picks from any one category.
    varied, per_category = [], Counter()
    for p in picks:
        if per_category[p.category] < 3:
            varied.append(p)
            per_category[p.category] += 1
        if len(varied) >= limit:
            break
    return profile, varied


# ---------- Endpoints ----------

def _user(authorization: str | None) -> int:
    user_id = current_user_id(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Log in to see your profile.")
    return user_id


@router.get("/me/profile")
def my_profile(authorization: str | None = Header(default=None)) -> CustomerProfile:
    """The logged-in shopper's profile: preferences worked out from orders, views and chats,
    plus their order history."""
    with get_db() as conn:
        profile, _, _ = build_profile(conn, _user(authorization))
    return profile


class RecommendationsOut(BaseModel):
    profile: CustomerProfile
    recommendations: list[Recommendation]


@router.get("/me/recommendations")
def my_recommendations(authorization: str | None = Header(default=None)) -> RecommendationsOut:
    """Up to 8 in-stock picks tailored to the logged-in shopper, each with a reason."""
    with get_db() as conn:
        profile, picks = recommend(conn, _user(authorization))
    return RecommendationsOut(profile=profile, recommendations=picks)
