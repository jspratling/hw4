"""Problem 9: usability improvements (backend).

Run with:  cd backend  then  .venv\\Scripts\\python.exe -m pytest tests/test_usability.py -v
Uses a temporary copy of campus_customs.db, so real data never changes. No API key needed.
"""

import shutil
import sqlite3
import sys
import types
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import checks  # noqa: E402
import db  # noqa: E402
import main  # noqa: E402
import memory  # noqa: E402
import search_path  # noqa: E402
import tagging  # noqa: E402
import tools  # noqa: E402
from models import CustomerInfo, ShopDeps  # noqa: E402

HOODIE = "basic-hoodie-big-yale"
EMAIL = "usability.test@yale.edu"


@pytest.fixture()
def env(tmp_path, monkeypatch):
    path = tmp_path / "campus_customs.db"
    shutil.copy(db.DB_PATH, path)
    for module in (db, memory, main):
        monkeypatch.setattr(module, "DB_PATH", path)
    monkeypatch.setattr(search_path, "LOG_PATH", tmp_path / "search_path.jsonl")
    monkeypatch.setattr(checks, "LOG_PATH", tmp_path / "checks.jsonl")
    memory.init_memory_tables()
    main.init_orders_tables()
    with db.get_db() as conn:
        tagging.init_tags_table(conn)
        conn.execute("DELETE FROM users WHERE email = ?", (EMAIL,))
    client = TestClient(main.app)
    client.post("/api/register", json={"first_name": "Ada", "last_name": "Lovelace", "email": EMAIL,
                                       "password": "bulldogs123", "confirm_password": "bulldogs123"})
    token = client.post("/api/login", json={"email": EMAIL, "password": "bulldogs123"}).json()["token"]
    with sqlite3.connect(path) as conn:
        user_id = conn.execute("SELECT id FROM users WHERE email = ?", (EMAIL,)).fetchone()[0]
    return client, path, {"Authorization": f"Bearer {token}"}, user_id


def ctx(path, customer=None):
    return types.SimpleNamespace(deps=ShopDeps(db_path=path, customer=customer))


# ---------- Backend 1: tags, live stock, seasons ----------

def test_every_product_is_tagged(env):
    _, path, _, _ = env
    with sqlite3.connect(path) as conn:
        tags = tagging.load_tags(conn)
        products = conn.execute("SELECT COUNT(*) FROM catalogue").fetchone()[0]
    assert len(tags) == products
    for t in tags.values():
        assert t["category"] in tagging.CATEGORIES and t["style"] in tagging.STYLES
        assert t["seasons"] and set(t["seasons"]) <= set(tagging.SEASONS)
    assert all(t["style"] == "Formal" for t in tags.values() if t["category"] == "Quarter-zips")
    assert tags["champion-full-zip-hood"]["brand"] == "Champion"


def test_seasons_follow_the_calendar():
    assert tagging.seasons_now(date(2026, 10, 16)) == ["Fall & winter", "Game day"]
    assert tagging.seasons_now(date(2026, 6, 1)) == ["Spring & summer"]
    assert tagging.seasons_now(date(2027, 1, 10)) == ["Fall & winter"]


def test_products_api_has_tags_live_stock_and_is_never_cached(env):
    client, path, _, _ = env
    res = client.get("/api/products")
    assert res.headers["cache-control"] == "no-store"
    hoodie = next(p for p in res.json() if p["product_id"] == HOODIE)
    assert {"category", "brand", "style", "color_groups", "seasons", "in_season", "sizes_in_stock"} <= set(hoodie)
    with sqlite3.connect(path) as conn:
        in_stock = {s for s, q in conn.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (HOODIE,)) if q}
    assert set(hoodie["sizes_in_stock"]) == in_stock


def test_stock_and_price_changes_show_up_immediately(env):
    client, path, _, _ = env
    before = client.get(f"/api/products/{HOODIE}/stock").json()
    with sqlite3.connect(path) as conn:  # a sale empties size M and the price changes
        conn.execute("UPDATE inventory SET quantity = 0 WHERE product_id = ? AND size = 'M'", (HOODIE,))
        conn.execute("UPDATE catalogue SET price = 59.0 WHERE product_id = ?", (HOODIE,))
    after = client.get(f"/api/products/{HOODIE}/stock").json()
    assert after["price"] == 59.0 and before["price"] != 59.0
    assert next(s["quantity"] for s in after["inventory"] if s["size"] == "M") == 0
    assert "checked_at" in after
    assert client.get("/api/products/no-such-item/stock").status_code == 404


def test_browse_catalogue_tool_filters_by_tags_and_stock(env):
    _, path, _, _ = env
    results = tools.browse_catalogue(ctx(path), style="formal", size="M", max_price=80)
    assert results and all(r.style == "Formal" and r.price <= 80 and "M" in r.sizes_in_stock for r in results)
    champion = tools.browse_catalogue(ctx(path), brand="champion", limit=20)
    assert champion and all(r.brand == "Champion" for r in champion)
    seasonal = tools.browse_catalogue(ctx(path), in_season_now=True, limit=20)
    assert all(r.in_season for r in seasonal)
    assert isinstance(tools.browse_catalogue(ctx(path), brand="Champion", max_price=1), str)


# ---------- Backend 2: profile and recommendations ----------

def place_order(path, user_id, product_id, size, quantity=1):
    with sqlite3.connect(path) as conn:
        price = conn.execute("SELECT price FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()[0]
        order_id = conn.execute("INSERT INTO orders (user_id, total) VALUES (?, ?)",
                                (user_id, price * quantity)).lastrowid
        conn.execute("INSERT INTO order_items (order_id, product_id, size, quantity, unit_price) "
                     "VALUES (?, ?, ?, ?, ?)", (order_id, product_id, size, quantity, price))


def test_profile_and_recommendations_use_orders_and_views(env):
    client, path, auth, user_id = env
    assert client.get("/api/me/recommendations").status_code == 401

    place_order(path, user_id, HOODIE, "M", 2)
    client.post("/api/views", headers=auth, json={"product_id": "champion-reverse-weave-hoodie-1"})

    profile = client.get("/api/me/profile", headers=auth).json()
    assert profile["usual_size"] == "M"
    assert profile["favorite_categories"][0] == "Hoodies"
    assert profile["orders"][0]["items"][0]["product_id"] == HOODIE

    picks = client.get("/api/me/recommendations", headers=auth).json()["recommendations"]
    assert 0 < len(picks) <= 8
    assert HOODIE not in [p["product_id"] for p in picks]  # already bought
    assert all("M" in p["sizes_in_stock"] for p in picks)  # in their size
    assert picks[0]["category"] == "Hoodies" and "in your size M" in picks[0]["reason"]
    assert all(p["image_url"].startswith("/media/") and p["description"] for p in picks)  # card needs both


def test_recommend_tool_and_agent_context(env):
    client, path, auth, user_id = env
    place_order(path, user_id, HOODIE, "L")
    assert isinstance(tools.recommend_for_me(ctx(path)), str)  # guest
    customer = CustomerInfo(user_id=user_id, first_name="Ada", last_name="Lovelace", email=EMAIL)
    picks = tools.recommend_for_me(ctx(path, customer), limit=3)
    assert len(picks) == 3 and all("L" in p.sizes_in_stock for p in picks)

    deps = memory.build_deps(user_id, None)
    assert "usual size L" in deps.customer.profile_summary
