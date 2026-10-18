"""Problem 12: append-only audit trail of the agent loop (output/audit_trail.json).

Run with:  cd backend  then  .venv\\Scripts\\python.exe -m pytest tests/test_audit.py -v
Uses a stand-in model and a temporary audit file, so no API key is needed and the real
audit trail is not touched.
"""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import agent  # noqa: E402
import audit  # noqa: E402
import db  # noqa: E402
from models import CustomerInfo, ShopDeps  # noqa: E402


@pytest.fixture()
def trail(tmp_path, monkeypatch):
    path = tmp_path / "audit_trail.json"
    monkeypatch.setattr(audit, "AUDIT_PATH", path)
    monkeypatch.setenv("PORTKEY_API_KEY", "test-key-not-used")
    agent.get_agent.cache_clear()
    yield path
    agent.get_agent.cache_clear()


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def search_then_answer(messages, info: AgentInfo):
    if not any(isinstance(m, ModelResponse) for m in messages):
        return ModelResponse(parts=[ToolCallPart("search_products", {"garment_type": "hoodie", "limit": 5})])
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
        "reply": "I put a few hoodies on the page for you.",
        "product_ids": ["basic-hoodie-big-yale"],
    })])


def ask(question, model_fn, deps=None):
    with agent.get_agent().override(model=FunctionModel(model_fn)):
        return run(agent.ask_shop_agent(question, [], deps))


def test_normal_run_is_recorded(trail):
    ask("what hoodies do you have?", search_then_answer)
    entries = audit.read_trail()
    events = [e["event"] for e in entries]
    assert events == ["run_start", "tool_call", "tool_call", "run_end"]
    start, search, final, end = entries
    assert start["question"] == "what hoodies do you have?" and start["shopper"] == "guest"
    assert search["tool"] == "search_products" and search["loop"] == 1
    assert '"garment_type": "hoodie"' in search["args"]
    assert search["result"].startswith("5 products: ")
    assert final["tool"] == "final_result" and final["loop"] == 2
    assert end["stop_reason"] == "final_answer"
    assert end["loops_used"] == 2
    assert end["product_ids"] == ["basic-hoodie-big-yale"]
    assert all(e["time"].startswith("20") for e in entries)
    assert len({e["run_id"] for e in entries}) == 1


def test_loop_limit_is_recorded(trail):
    def keeps_searching(messages, info):
        return ModelResponse(parts=[ToolCallPart("search_products", {"query": "hoodie"})])

    reply, _ = ask("show me everything", keeps_searching)
    end = audit.read_trail()[-1]
    assert reply.reply == agent.LOOP_LIMIT_REPLY
    assert end["stop_reason"] == "loop_limit"
    assert end["loops_used"] == 3
    assert end["tools_called"] == ["search_products"] * 3


def test_error_is_recorded_and_still_raised(trail):
    def broken(messages, info):
        raise RuntimeError("model unavailable")

    with pytest.raises(RuntimeError):
        ask("hello", broken)
    end = audit.read_trail()[-1]
    assert end["stop_reason"] == "error"
    assert "model unavailable" in end["error"]


def test_trail_is_append_only_and_never_wiped(trail):
    ask("first question", search_then_answer)
    first = trail.read_bytes()
    ask("second question", search_then_answer)
    second = trail.read_bytes()

    # Everything from the first run is still there, byte for byte (only the closing "]" moved).
    assert second.startswith(first.rstrip()[:-1].rstrip())
    entries = json.loads(second)  # still one valid JSON list
    questions = [e["question"] for e in entries if e["event"] == "run_start"]
    assert questions == ["first question", "second question"]


def test_hand_edited_file_is_not_touched(trail):
    trail.write_text('[{"note": "kept"}]\nsomething typed by hand', encoding="utf-8")
    before = trail.read_bytes()
    ask("third question", search_then_answer)
    assert trail.read_bytes().startswith(before)


def test_no_customer_details_in_the_trail(trail):
    customer = CustomerInfo(user_id=77, first_name="Grace", last_name="Hopper", email="grace@yale.edu")
    ask("what hoodies do you have?", search_then_answer, ShopDeps(db_path=db.DB_PATH, customer=customer))
    text = trail.read_text(encoding="utf-8")
    assert '"shopper": "logged_in"' in text
    for private in ("Grace", "Hopper", "grace@yale.edu", '"user_id"'):
        assert private not in text
