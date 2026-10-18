"""Problem 10: sport and field-of-study themes, and the chat persona that goes with them.

Run with:  cd backend  then  .venv\\Scripts\\python.exe -m pytest tests/test_design.py -v
"""

import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import agent  # noqa: E402
import checks  # noqa: E402
import db  # noqa: E402
import main  # noqa: E402
import memory  # noqa: E402
import search_path  # noqa: E402
import themes  # noqa: E402
from models import ShopDeps, ShopReply  # noqa: E402


@pytest.mark.parametrize("question,key,kind", [
    ("what hockey hoodies do you have?", "hockey", "sport"),
    ("field hockey tee for my sister", "field-hockey", "sport"),
    ("anything for the Harvard-Yale game?", "football", "sport"),
    ("School of Management attire for interviews", "management", "field"),
    ("I'm pre-med, what do you have?", "medicine", "field"),
    ("School of Art fleece", "art", "field"),
])
def test_questions_pick_the_right_theme(question, key, kind):
    t = themes.detect_theme(question)
    assert t is not None and (t.key, t.kind) == (key, kind)


@pytest.mark.parametrize("question", ["a navy crewneck sweatshirt", "show me something warm", "a crew neck tee"])
def test_everyday_questions_have_no_theme(question):
    assert themes.detect_theme(question) is None


def test_agent_speaks_as_the_theme_persona():
    som = themes.THEMES_BY_KEY["management"]
    text = agent.customer_context(ShopDeps(db_path=Path("x"), theme=som))
    assert som.persona in text and "business professional" in text and "automated assistant" in text


@pytest.fixture()
def client(tmp_path, monkeypatch):
    path = tmp_path / "campus_customs.db"
    shutil.copy(db.DB_PATH, path)
    for module in (db, memory, main):
        monkeypatch.setattr(module, "DB_PATH", path)
    monkeypatch.setattr(search_path, "LOG_PATH", tmp_path / "search_path.jsonl")
    monkeypatch.setattr(checks, "LOG_PATH", tmp_path / "checks.jsonl")
    seen = []

    async def fake_agent(message, history, deps=None):
        seen.append(deps)
        ids = ["ice-hockey-left-chest-hoodie", "yale-sports-hoodie-hockey"] if "show" in message else []
        return ShopReply(reply="ok", product_ids=ids), []

    monkeypatch.setattr(main, "ask_shop_agent", fake_agent)
    return TestClient(main.app), seen


def test_chat_returns_theme_and_keeps_it_for_follow_ups(client):
    c, seen = client
    first = c.post("/api/chat", json={"message": "School of Management attire?"}).json()
    assert first["theme"]["key"] == "management" and seen[-1].theme.persona == "Morgan"

    # A follow-up with no theme words keeps the theme already on screen.
    c.post("/api/chat", json={"message": "what about in gray?", "theme_key": "management"})
    assert seen[-1].theme.key == "management"

    # No theme words at all, but the cards shown are hockey items -> hockey banner.
    shown = c.post("/api/chat", json={"message": "show me your bestsellers"}).json()
    assert shown["theme"]["key"] == "hockey"


def test_products_search_theme_endpoint(client):
    c, _ = client
    assert c.get("/api/themes/detect", params={"q": "school of management"}).json()["theme"]["key"] == "management"
    assert c.get("/api/themes/detect", params={"q": "navy crewneck"}).json()["theme"] is None
