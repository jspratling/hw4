"""Live tests: does prompts/prompt.md make the agent call the right tools and answer from the database?

These call the real AI model through Portkey, so they are skipped unless you opt in:

    cd backend
    $env:RUN_LIVE_AGENT_TESTS = "1"
    .\\.venv\\Scripts\\python.exe -m pytest tests/test_agent_prompt.py -v

Expected answers are read from campus_customs.db when the test runs, so they stay correct
even after purchases change the stock.
"""

import asyncio
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest
from pydantic_ai.messages import ToolCallPart

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from agent import ask_shop_agent  # noqa: E402
from checks import verify_chat_reply  # noqa: E402
from db import DB_PATH  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_AGENT_TESTS") != "1",
    reason="Live model test. Set RUN_LIVE_AGENT_TESTS=1 to run.",
)


def db_row(sql: str, *args):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(sql, args).fetchone()


# One event loop for every test: the agent's HTTP client is cached and tied to the loop
# it was created on (the FastAPI server also uses a single loop).
LOOP = asyncio.new_event_loop()


def ask(question: str):
    answer, messages = LOOP.run_until_complete(ask_shop_agent(question, []))
    tools_called = {
        part.tool_name
        for m in messages
        for part in getattr(m, "parts", [])
        if isinstance(part, ToolCallPart)
    }
    fact_check = verify_chat_reply(answer, messages, question)
    print(f"\nQ: {question}\nA: {answer.reply}\nTools: {sorted(tools_called)}")
    return answer, tools_called, fact_check


def test_price_and_description_question_uses_details_tool():
    name, price, description = db_row(
        "SELECT name, price, description FROM catalogue WHERE product_id = 'baseball-left-chest-crewneck'"
    )
    answer, tools_called, fact_check = ask(f"What does the {name} look like, and how much is it?")
    assert "get_product_details" in tools_called
    assert f"${price:.2f}" in answer.reply
    assert fact_check.passed, fact_check.issues
    assert "baseball-left-chest-crewneck" in answer.product_ids


def test_sold_out_size_is_said_clearly():
    pid, size = db_row(
        "SELECT i.product_id, i.size FROM inventory i JOIN catalogue c USING (product_id) "
        "WHERE i.quantity = 0 AND i.size = 'M' ORDER BY c.name LIMIT 1"
    )
    name = db_row("SELECT name FROM catalogue WHERE product_id = ?", pid)[0]
    answer, tools_called, fact_check = ask(f"Is the {name} available in medium?")
    assert tools_called & {"check_stock", "get_product_details"}
    assert re.search(r"sold[\s-]out", answer.reply, re.IGNORECASE), answer.reply
    assert fact_check.passed, fact_check.issues


def test_how_many_left_gives_exact_quantity():
    name, qty = db_row(
        "SELECT c.name, i.quantity FROM inventory i JOIN catalogue c USING (product_id) "
        "WHERE c.product_id = 'basic-hoodie-big-yale' AND i.size = 'XS'"
    )
    answer, tools_called, fact_check = ask(f"How many {name} are left in extra small?")
    assert tools_called & {"check_stock", "get_product_details"}
    assert re.search(rf"\b{qty}\b", answer.reply), answer.reply
    assert fact_check.passed, fact_check.issues


def test_sold_out_sizes_listed_from_database():
    name = db_row("SELECT name FROM catalogue WHERE product_id = 'crew-left-chest-hoodie'")[0]
    with sqlite3.connect(DB_PATH) as conn:
        sold_out = [r[0] for r in conn.execute(
            "SELECT size FROM inventory WHERE product_id = 'crew-left-chest-hoodie' AND quantity = 0")]
    answer, tools_called, fact_check = ask(f"Which sizes of the {name} are sold out?")
    assert tools_called & {"check_stock", "get_product_details"}
    for size in sold_out:
        assert re.search(rf"\b{size}\b", answer.reply), f"{size} missing from: {answer.reply}"
    assert fact_check.passed, fact_check.issues


def test_product_we_dont_carry_gets_no_invented_price():
    answer, tools_called, fact_check = ask("How much is your Yale bulldog plush toy?")
    assert "search_products" in tools_called
    assert fact_check.passed, fact_check.issues
