"""Problem 7: the chat search path is logged from the question all the way to the page.

Run with:  cd backend  then  .venv\\Scripts\\python.exe -m pytest tests/test_search_path.py -v
The agent is replaced with a stand-in, so no API key is needed and no real data changes.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import checks  # noqa: E402
import main  # noqa: E402
import search_path  # noqa: E402
from models import ShopReply  # noqa: E402

HOODIES = ["basic-hoodie-big-yale", "crew-left-chest-hoodie"]


def fake_run():
    """What one agent run looks like: a search_products call and its result."""
    return [
        ModelResponse(parts=[ToolCallPart(tool_name="search_products",
                                          args={"query": "hoodie", "garment_type": "hoodie"},
                                          tool_call_id="c1")]),
        ModelRequest(parts=[ToolReturnPart(tool_name="search_products", tool_call_id="c1",
                                           content=[{"product_id": pid, "price": 68.0} for pid in HOODIES])]),
    ]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(search_path, "LOG_PATH", tmp_path / "search_path.jsonl")
    monkeypatch.setattr(checks, "LOG_PATH", tmp_path / "checks.jsonl")

    async def fake_agent(message, history, deps=None):
        return ShopReply(reply="Here are our hoodies.", product_ids=HOODIES), fake_run()

    monkeypatch.setattr(main, "ask_shop_agent", fake_agent)
    return TestClient(main.app)


def test_backend_steps_follow_the_search_in_order():
    steps = search_path.backend_steps("abc123abc123", "what hoodies do you have?", fake_run(),
                                      HOODIES, [{"product_id": p, "name": p, "price": 68.0} for p in HOODIES])
    assert [s.step for s in steps] == ["chat_received", "tool_call", "tool_result", "agent_reply", "cards_built"]
    assert steps[1].detail == {"tool": "search_products", "inputs": {"query": "hoodie", "garment_type": "hoodie"}}
    assert steps[2].detail["product_ids"] == HOODIES
    assert [c["product_id"] for c in steps[4].detail["cards"]] == HOODIES


def test_chat_returns_search_id_and_logs_the_backend_path(client):
    res = client.post("/api/chat", json={"message": "what hoodies do you have?"})
    assert res.status_code == 200
    body = res.json()
    assert [p["product_id"] for p in body["products"]] == HOODIES
    search_id = body["search_id"]

    path = client.get(f"/api/search-path/{search_id}").json()
    assert [s["step"] for s in path] == ["chat_received", "tool_call", "tool_result", "agent_reply", "cards_built"]
    assert path[0]["detail"]["question"] == "what hoodies do you have?"


def test_page_events_complete_the_path(client):
    search_id = client.post("/api/chat", json={"message": "what hoodies do you have?"}).json()["search_id"]
    events = [
        {"event": "shown_on_page", "page": "/"},
        {"event": "card_opened", "page": "/", "product_id": HOODIES[0]},
        {"event": "added_to_cart", "page": "/", "product_id": HOODIES[0], "size": "L", "quantity": 1},
        {"event": "go_to_checkout", "page": "/", "product_id": HOODIES[0]},
    ]
    for e in events:
        assert client.post(f"/api/search-path/{search_id}/events", json=e).status_code == 200

    steps = [s["step"] for s in client.get(f"/api/search-path/{search_id}").json()]
    assert steps[-4:] == ["shown_on_page", "card_opened", "added_to_cart", "go_to_checkout"]


def test_unknown_or_bad_search_ids_are_rejected(client):
    assert client.post("/api/search-path/000000000000/events", json={"event": "card_opened"}).status_code == 404
    assert client.get("/api/search-path/not-an-id").status_code == 422
    search_id = client.post("/api/chat", json={"message": "hoodies"}).json()["search_id"]
    assert client.post(f"/api/search-path/{search_id}/events", json={"event": "hack"}).status_code == 422
