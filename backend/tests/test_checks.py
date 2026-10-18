"""Run with:  cd backend  then  .venv\\Scripts\\python.exe -m pytest tests -q

These tests use a temporary copy of campus_customs.db, so they never change real data.
"""

import shutil
import sys
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelRequest, ToolReturnPart

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import checks  # noqa: E402
import db  # noqa: E402
from models import ShopReply  # noqa: E402


@pytest.fixture()
def db_copy(tmp_path, monkeypatch) -> Path:
    path = tmp_path / "campus_customs.db"
    shutil.copy(db.DB_PATH, path)
    monkeypatch.setattr(db, "DB_PATH", path)
    return path


def tool_messages(*contents) -> list:
    return [ModelRequest(parts=[ToolReturnPart(tool_name="t", content=c) for c in contents])]


# ---------- hourly tool health ----------

def test_every_tool_matches_the_database(db_copy):
    report = checks.run_tool_checks(db_copy)
    assert report.passed, report.issues
    assert report.checked > 600  # 102 products x (details + 6 sizes) + searches


def test_tool_health_catches_a_wrong_price(db_copy, monkeypatch):
    import tools
    real = tools.get_product_details

    def lying(ctx, product_id):
        product = real(ctx, product_id)
        return product.model_copy(update={"price": product.price + 1})

    monkeypatch.setattr(tools, "get_product_details", lying)
    report = checks.run_tool_checks(db_copy)
    assert not report.passed
    assert any("tool price" in issue for issue in report.issues)


# ---------- inventory consistency ----------

def test_inventory_is_consistent(db_copy):
    assert checks.check_inventory(db_copy).passed


def test_inventory_check_catches_negative_stock(db_copy):
    import sqlite3
    with sqlite3.connect(db_copy) as conn:
        conn.execute("UPDATE inventory SET quantity = -1 WHERE id = 1")
    report = checks.check_inventory(db_copy)
    assert not report.passed


# ---------- after every chat ----------

FACTS = {"product_id": "ice-hockey-left-chest-hoodie", "price": 68.0,
         "inventory": [{"size": "M", "quantity": 0}, {"size": "XS", "quantity": 20}]}


def test_reply_with_database_facts_passes():
    answer = ShopReply(reply="It's $68.00 and sold out in medium, but 20 are left in XS.",
                       product_ids=["ice-hockey-left-chest-hoodie"])
    assert checks.verify_chat_reply(answer, tool_messages(FACTS)).passed


def test_invented_price_is_caught():
    answer = ShopReply(reply="It's only $49.99 today!", product_ids=["ice-hockey-left-chest-hoodie"])
    report = checks.verify_chat_reply(answer, tool_messages(FACTS))
    assert not report.passed and "$49.99" in report.issues[0]


def test_invented_stock_count_is_caught():
    answer = ShopReply(reply="We have 7 left in medium.")
    assert not checks.verify_chat_reply(answer, tool_messages(FACTS)).passed


def test_card_not_from_tools_is_caught():
    answer = ShopReply(reply="Try this one.", product_ids=["made-up-product"])
    assert not checks.verify_chat_reply(answer, tool_messages(FACTS)).passed


def test_price_without_any_lookup_is_caught():
    answer = ShopReply(reply="Hoodies are $68.00.")
    assert not checks.verify_chat_reply(answer, []).passed


# ---------- after every purchase ----------

def test_purchase_reduces_stock_and_passes_inventory_check(db_copy):
    import sqlite3
    from fastapi.testclient import TestClient
    import auth
    import main

    client = TestClient(main.app)
    with TestClient(main.app):
        pass  # runs startup (creates order tables)
    with sqlite3.connect(db_copy) as conn:
        before = conn.execute(
            "SELECT quantity FROM inventory WHERE product_id = 'basic-hoodie-big-yale' AND size = 'XS'"
        ).fetchone()[0]
    token = auth.create_token(1)
    res = client.post("/api/orders", headers={"Authorization": f"Bearer {token}"},
                      json={"items": [{"product_id": "basic-hoodie-big-yale", "size": "XS", "quantity": 2}]})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["inventory_check"]["passed"], body["inventory_check"]["issues"]
    assert body["total"] == 136.0
    with sqlite3.connect(db_copy) as conn:
        after = conn.execute(
            "SELECT quantity FROM inventory WHERE product_id = 'basic-hoodie-big-yale' AND size = 'XS'"
        ).fetchone()[0]
    assert after == before - 2


def test_cannot_buy_more_than_in_stock(db_copy):
    from fastapi.testclient import TestClient
    import auth
    import main

    with TestClient(main.app) as client:
        token = auth.create_token(1)
        res = client.post("/api/orders", headers={"Authorization": f"Bearer {token}"},
                          json={"items": [{"product_id": "ice-hockey-left-chest-hoodie",
                                           "size": "M", "quantity": 1}]})
    assert res.status_code == 409
    assert "sold out" in res.json()["detail"]
