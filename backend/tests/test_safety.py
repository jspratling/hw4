"""Problem 12: safety rules and specs (loop limit of 3, results capped at 5).

Run with:  cd backend  then  .venv\\Scripts\\python.exe -m pytest tests/test_safety.py -v
Uses a stand-in model (no API key or internet needed) and reads the database read-only.
"""

import asyncio
import sys
import types
from pathlib import Path

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import agent  # noqa: E402
import db  # noqa: E402
import tools  # noqa: E402
from models import MAX_AGENT_LOOPS, MAX_CARDS, MAX_RESULTS, ShopDeps, ShopReply  # noqa: E402

PROMPT = (BACKEND / "prompts" / "prompt.md").read_text(encoding="utf-8")


@pytest.fixture()
def shop_agent(monkeypatch, tmp_path):
    import audit
    monkeypatch.setattr(audit, "AUDIT_PATH", tmp_path / "audit_trail.json")  # keep the real trail clean
    monkeypatch.setenv("PORTKEY_API_KEY", "test-key-not-used")
    agent.get_agent.cache_clear()
    yield agent.get_agent()
    agent.get_agent.cache_clear()


def run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def model_requests(messages):
    return [m for m in messages if isinstance(m, ModelResponse)]


# ---------- Specs ----------

def test_spec_values():
    assert MAX_AGENT_LOOPS == 3
    assert MAX_RESULTS == 5
    assert MAX_CARDS == 5


def test_agent_loop_stops_after_3_steps(shop_agent):
    """A model that keeps searching forever is stopped after 3 steps with an honest reply."""
    def keeps_searching(messages, info: AgentInfo):
        return ModelResponse(parts=[ToolCallPart("search_products", {"query": "hoodie"})])

    with shop_agent.override(model=FunctionModel(keeps_searching)):
        reply, messages = run(agent.ask_shop_agent("show me everything you have", []))

    assert reply.reply == agent.LOOP_LIMIT_REPLY
    assert reply.product_ids == []
    assert len(model_requests(messages)) == MAX_AGENT_LOOPS
    # The fallback quotes no prices or stock, so nothing is made up.
    assert "$" not in reply.reply


def test_normal_question_fits_in_the_limit(shop_agent):
    """Search, then answer: 2 steps, well inside the limit of 3."""
    def search_then_answer(messages, info: AgentInfo):
        if len(model_requests(messages)) == 0:
            return ModelResponse(parts=[ToolCallPart("search_products", {"garment_type": "hoodie"})])
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "reply": "I put a few hoodies on the page for you.",
            "product_ids": ["basic-hoodie-big-yale"],
        })])

    with shop_agent.override(model=FunctionModel(search_then_answer)):
        reply, messages = run(agent.ask_shop_agent("what hoodies do you have?", []))

    assert reply.product_ids == ["basic-hoodie-big-yale"]
    assert len(model_requests(messages)) == 2


# ---------- Results capped at 5 ----------

def ctx():
    return types.SimpleNamespace(deps=ShopDeps(db_path=db.DB_PATH))


def test_search_tools_return_at_most_5():
    assert len(tools.search_products(ctx(), garment_type="hoodie", limit=50)) == 5
    assert len(tools.search_products(ctx(), garment_type="hoodie")) == 5
    assert len(tools.browse_catalogue(ctx(), limit=50)) == 5


def test_at_most_5_cards():
    ids = [f"item-{i}" for i in range(9)]
    assert ShopReply(reply="Here you go.", product_ids=ids).product_ids == ids[:5]


# ---------- Safety rules in prompts/prompt.md ----------

@pytest.mark.parametrize("rule", [
    "Do not make up prices",
    "Do not make up stock levels",
    "Do not share customer information",
    "Do not place orders without the shopper confirming",
    "Stay on topic with what the customer is requesting",
    "At most 3 steps per message",
    "At most 5 results",
])
def test_safety_rules_are_in_the_prompt(rule):
    assert rule in PROMPT


def test_agent_has_no_tool_that_places_orders_or_reads_customers():
    names = {t.__name__ for t in tools.SHOP_TOOLS}
    assert names == {"search_products", "get_product_details", "check_stock",
                     "browse_catalogue", "recommend_for_me"}
