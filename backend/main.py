"""Campus Customs API: product catalogue, product images, accounts and the shop chatbot.

Run from the backend/ folder:  python -m uvicorn main:app --port 8000
The chatbot is a PydanticAI agent kept in agent.py, tools.py, models.py and
prompts/prompt.md next to this file.
"""

import asyncio
import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException, Path
from fastapi.staticfiles import StaticFiles

from agent import AgentNotConfigured, ask_shop_agent
from auth import current_user_id
from auth import router as auth_router
from checks import CheckReport, check_inventory, record, run_tool_checks, verify_chat_reply
from db import DATA_DIR, DB_PATH, get_db
from models import ChatRequest, ChatResponse, ProductCard, ShopDeps
from memory import agent_history, build_deps, init_memory_tables, save_turn
from memory import router as memory_router
from customer_profile import router as profile_router
from orders import init_orders_tables
from orders import router as orders_router
from themes import THEMES_BY_KEY, detect_theme
from tagging import SEASONS, init_tags_table, is_in_season, load_tags, seasons_now
from search_path import PageEventIn, PathStep, log_backend_path, log_page_event, new_search_id, read_path
from tools import load_products

logger = logging.getLogger("campus_customs")
if not logger.handlers:  # Uvicorn configures its own loggers, so give ours a handler too.
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False

HEALTH_CHECK_SECONDS = 60 * 60  # hourly
latest_reports: dict[str, CheckReport] = {}


def run_scheduled_checks() -> None:
    for report in (run_tool_checks(DB_PATH), check_inventory(DB_PATH)):
        latest_reports[report.check] = record(report)


async def hourly_checks() -> None:
    while True:
        try:
            await asyncio.to_thread(run_scheduled_checks)
        except Exception:
            logger.exception("Scheduled checks crashed")
        await asyncio.sleep(HEALTH_CHECK_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_orders_tables()
    init_memory_tables()
    with get_db() as conn:  # Problem 9: tag every product (category, brand, style, colors, seasons)
        logger.info("Tagged %d products", init_tags_table(conn))
    task = asyncio.create_task(hourly_checks())  # runs once at startup, then every hour
    yield
    task.cancel()


app = FastAPI(title="Campus Customs API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(orders_router)
app.include_router(memory_router)
app.include_router(profile_router)

# Only the product photos are public. catalogue.image_file_path is relative to
# data/ (e.g. "products/x.jpg"), so it maps to /media/products/x.jpg.
app.mount("/media/products", StaticFiles(directory=DATA_DIR / "products"), name="media")


SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


def product_from_row(r: sqlite3.Row, tags: dict | None = None) -> dict:
    product = {
        "product_id": r["product_id"],
        "name": r["name"],
        "garment_type": r["garment_type"],
        "description": r["description"],
        "colors": json.loads(r["colors"]),
        "price": r["price"],
        "image_url": f"/media/{r['image_file_path']}",
    }
    if tags:
        # Problem 9: metadata tags used by the filters, the style toggle and seasonal picks.
        product.update({
            "category": tags["category"],
            "brand": tags["brand"],
            "style": tags["style"],
            "color_groups": tags["color_groups"],
            "seasons": tags["seasons"],
            "in_season": is_in_season(tags["seasons"]),
        })
    return product


def _sorted_stock(rows) -> list[dict]:
    return sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in rows),
        key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else len(SIZE_ORDER),
    )


@app.get("/api/products")
def list_products() -> list[dict]:
    """Every product with its tags and current stock by size (read live, never cached)."""
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        tags = load_tags(conn)
        stock: dict[str, list] = {}
        for s in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(s["product_id"], []).append(s)
    products = []
    for r in rows:
        inventory = _sorted_stock(stock.get(r["product_id"], []))
        products.append({
            **product_from_row(r, tags.get(r["product_id"])),
            "sizes_in_stock": [s["size"] for s in inventory if s["quantity"] > 0],
            "total_stock": sum(s["quantity"] for s in inventory),
        })
    return products


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()
        tags = load_tags(conn).get(product_id)
    inventory = _sorted_stock(stock)
    return {
        **product_from_row(row, tags),
        "inventory": inventory,
        "total_stock": sum(s["quantity"] for s in inventory),
    }


@app.get("/api/products/{product_id}/stock")
def live_stock(product_id: str) -> dict:
    """Problem 9: up-to-the-minute price and stock for one product. The item page and popup
    call this every 30 seconds so a size that sells out disappears while the shopper looks."""
    with get_db() as conn:
        row = conn.execute("SELECT price FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()
    inventory = _sorted_stock(stock)
    return {
        "product_id": product_id,
        "price": row["price"],
        "inventory": inventory,
        "total_stock": sum(s["quantity"] for s in inventory),
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@app.get("/api/themes/detect")
def theme_for_search(q: str = "") -> dict:
    """Problem 10: sport or field-of-study theme for a Products page search (or null)."""
    theme = detect_theme(q[:200])
    return {"theme": theme.model_dump() if theme else None}


@app.get("/api/seasons/now")
def current_seasons() -> dict:
    """Problem 9: which seasonal collections are featured today (changes automatically by date)."""
    return {"seasons": seasons_now(), "all_seasons": SEASONS}


@app.middleware("http")
async def no_stale_data(request, call_next):
    """Problem 9: prices and stock must always be current, so API answers are never cached
    by the browser. Product photos can still be cached."""
    response = await call_next(request)
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.post("/api/chat")
async def chat(request: ChatRequest, authorization: str | None = Header(default=None)) -> ChatResponse:
    """A chat message from the website goes to the shop agent; its reply comes back
    with product cards built from the database (never from the model's own text).

    Problem 8: for a logged-in shopper the agent gets their saved history from the
    database plus who they are and which page they are on, and the turn is saved.
    Guests can chat too; their history comes from the browser and is not saved."""
    user_id = current_user_id(authorization)
    deps = build_deps(user_id, request.page)
    # Problem 10: a sport or field of study in the question (or the theme already on screen)
    # sets the chat persona: a coach for sports, a professional for a school or major.
    deps.theme = detect_theme(request.message) or THEMES_BY_KEY.get(request.theme_key or "")
    history = agent_history(user_id) if deps.customer else request.history
    try:
        answer, run_messages = await ask_shop_agent(request.message, history, deps)
    except AgentNotConfigured as exc:
        logger.error("Chat agent not configured: %s", exc)
        raise HTTPException(status_code=503, detail="The shopping assistant is not set up yet.")
    except Exception:
        logger.exception("Chat agent failed")
        raise HTTPException(
            status_code=502,
            detail="The shopping assistant had trouble answering. Please try again.",
        )

    # After-interaction test: every fact in the reply must match what the tools read.
    fact_check = record(verify_chat_reply(answer, run_messages, request.message))
    latest_reports[fact_check.check] = fact_check

    products = load_products(ShopDeps(db_path=DB_PATH), answer.product_ids)
    cards = [ProductCard(**p.model_dump(exclude={"search_tags"})) for p in products]

    # Problem 7: log the path this search took (chat -> tools -> agent -> cards).
    # The website adds the rest (shown on page, card opened, cart, checkout) by search_id.
    search_id = new_search_id()
    log_backend_path(search_id, request.message, run_messages, answer.product_ids,
                     [c.model_dump() for c in cards])

    if deps.customer:
        save_turn(deps.customer.user_id, request.message, answer.reply, cards)

    return ChatResponse(
        reply=answer.reply,
        follow_up_question=answer.follow_up_question,
        facts_verified=fact_check.passed,
        products=cards,
        search_id=search_id,
        theme=deps.theme or _theme_from_cards(request.message, answer.product_ids),
    )


def _theme_from_cards(message: str, product_ids: list[str]):
    """If the question had no theme, use what most of the shown products have in common."""
    with get_db() as conn:
        return detect_theme(message, product_ids, conn)


SEARCH_ID = Path(pattern=r"^[0-9a-f]{12}$")


@app.post("/api/search-path/{search_id}/events")
def search_path_event(event: PageEventIn, search_id: str = SEARCH_ID) -> PathStep:
    """The website reports what happened after the chat's matches reached the page."""
    if not read_path(search_id):
        raise HTTPException(status_code=404, detail="Unknown search_id")
    return log_page_event(search_id, event)


@app.get("/api/search-path/{search_id}")
def search_path(search_id: str = SEARCH_ID) -> list[PathStep]:
    """The full logged path for one chat search, from the question to the page."""
    steps = read_path(search_id)
    if not steps:
        raise HTTPException(status_code=404, detail="Unknown search_id")
    return steps


@app.get("/api/health/checks")
def health_checks() -> dict[str, CheckReport]:
    """Latest result of each automatic check (tool health, inventory, last chat fact check)."""
    return latest_reports


@app.post("/api/health/checks/run")
async def run_checks_now() -> dict[str, CheckReport]:
    """Run the tool health and inventory checks immediately instead of waiting for the hour."""
    await asyncio.to_thread(run_scheduled_checks)
    return latest_reports
