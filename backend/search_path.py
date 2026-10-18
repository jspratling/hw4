"""Search path log (Problem 7): how a chat search reached the page.

Every chat message gets a search_id. Each step the search takes is written as one
line to backend/logs/search_path.jsonl, all sharing that search_id:

  Backend (written by /api/chat):
    1. chat_received  - the shopper's words arrived from the website's chat widget
    2. tool_call      - the agent called a database tool (name + inputs)
    3. tool_result    - what that tool found (product ids, or a "not found" message)
    4. agent_reply    - the product_ids the agent chose to show
    5. cards_built    - the product cards the backend built from the database and sent back

  Website (sent to POST /api/search-path/{search_id}/events):
    6. shown_on_page  - the matches appeared on the main page (which page)
    7. card_opened    - the shopper clicked a card and the item popup opened
    8. added_to_cart  - the shopper added that item to the cart from the popup
    9. go_to_checkout - the shopper went to checkout from the popup
       full_page_opened - the shopper opened the full single-item page from the popup

View one search's full path at GET /api/search-path/{search_id}.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessage, ToolCallPart, ToolReturnPart
from pydantic_core import to_jsonable_python

logger = logging.getLogger("campus_customs.search_path")

LOG_PATH = Path(__file__).resolve().parent / "logs" / "search_path.jsonl"

PageEvent = Literal["shown_on_page", "card_opened", "added_to_cart", "go_to_checkout", "full_page_opened"]


class PathStep(BaseModel):
    search_id: str
    step: str
    at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))
    detail: dict[str, Any] = {}


class PageEventIn(BaseModel):
    """A step the website reports after the matches reach the page."""

    event: PageEvent
    page: str = Field(default="", max_length=200)
    product_id: str | None = Field(default=None, max_length=200)
    size: str | None = Field(default=None, max_length=10)
    quantity: int | None = Field(default=None, ge=1, le=100)


def new_search_id() -> str:
    return uuid.uuid4().hex[:12]


def _write(steps: list[PathStep]) -> None:
    try:
        LOG_PATH.parent.mkdir(exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            for s in steps:
                f.write(s.model_dump_json() + "\n")
    except OSError:
        logger.exception("Could not write %s", LOG_PATH)


def _product_ids(value: Any) -> list[str]:
    """Product ids found anywhere in a tool result, in order, without duplicates."""
    found: list[str] = []

    def walk(v: Any) -> None:
        if isinstance(v, dict):
            if isinstance(v.get("product_id"), str) and v["product_id"] not in found:
                found.append(v["product_id"])
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)

    walk(value)
    return found


def backend_steps(
    search_id: str,
    question: str,
    run_messages: list[ModelMessage],
    chosen_ids: list[str],
    cards: list[dict],
) -> list[PathStep]:
    """Turn one agent run into the backend half of the search path."""
    steps = [PathStep(search_id=search_id, step="chat_received",
                      detail={"question": question[:500], "route": "POST /api/chat"})]
    for message in run_messages:
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolCallPart):
                steps.append(PathStep(search_id=search_id, step="tool_call",
                                      detail={"tool": part.tool_name, "inputs": part.args_as_dict()}))
            elif isinstance(part, ToolReturnPart):
                content = to_jsonable_python(part.content)
                ids = _product_ids(content)
                detail: dict[str, Any] = {"tool": part.tool_name, "products_found": len(ids),
                                          "product_ids": ids[:20]}
                if isinstance(content, str):
                    detail["message"] = content[:300]
                steps.append(PathStep(search_id=search_id, step="tool_result", detail=detail))
    steps.append(PathStep(search_id=search_id, step="agent_reply",
                          detail={"product_ids": chosen_ids}))
    steps.append(PathStep(search_id=search_id, step="cards_built", detail={
        "source": "catalogue + inventory tables",
        "cards": [{"product_id": c["product_id"], "name": c["name"], "price": c["price"]} for c in cards],
    }))
    return steps


def log_backend_path(search_id: str, question: str, run_messages: list[ModelMessage],
                     chosen_ids: list[str], cards: list[dict]) -> list[PathStep]:
    steps = backend_steps(search_id, question, run_messages, chosen_ids, cards)
    _write(steps)
    tools_used = [s.detail["tool"] for s in steps if s.step == "tool_call"]
    logger.info("search %s: %r -> tools %s -> %d cards", search_id, question[:80],
                tools_used or "none", len(cards))
    return steps


def log_page_event(search_id: str, event: PageEventIn) -> PathStep:
    step = PathStep(search_id=search_id, step=event.event,
                    detail=event.model_dump(exclude={"event"}, exclude_none=True))
    _write([step])
    logger.info("search %s: %s %s", search_id, event.event, event.product_id or event.page)
    return step


def read_path(search_id: str) -> list[PathStep]:
    """Every logged step for one search, in the order it happened."""
    if not LOG_PATH.exists():
        return []
    steps = []
    with LOG_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("search_id") == search_id:
                steps.append(PathStep(**data))
    return steps
