"""Customer memory (Problem 8).

Logged-in shoppers:
  - every chat turn (their message and the assistant's reply, with the product cards shown)
    is saved in the chat_messages table and reloaded when they log in again;
  - every product page or product popup they open is saved in the product_views table, so
    the site can take them back to the last product they looked at;
  - the agent is told who they are (first name, last name, email), what page they are on,
    the last product they viewed and their last search, through ShopDeps (see agent.py).

Guests can still chat, but nothing about them is saved.
"""

import json
import re
import sqlite3

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from auth import current_user_id
from db import DB_PATH, get_db
from models import LOW_STOCK_THRESHOLD, ChatTurn, CustomerInfo, PageContext, ProductCard, ProductDetail, ShopDeps
from tools import load_products

router = APIRouter(prefix="/api")

HISTORY_FOR_AGENT = 20  # most recent saved turns the agent sees
HISTORY_FOR_WIDGET = 50  # most recent saved turns shown in the chat window
SIMILAR = "Suggest similar items"  # welcome-back button text


def init_memory_tables() -> None:
    """chat_messages already exists in campus_customs.db; product_views is new for Problem 8."""
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                products_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS product_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                viewed_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES catalogue(product_id)
            );
            CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id);
            CREATE INDEX IF NOT EXISTS idx_product_views_user ON product_views (user_id, id);
            """
        )


# ---------- Reading and writing ----------

def load_customer(user_id: int) -> CustomerInfo | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    first, _, last = (row["name"] or "").partition(" ")
    return CustomerInfo(
        user_id=row["id"],
        first_name=row["first_name"] or first,
        last_name=row["last_name"] or last,
        email=row["email"],
    )


def save_turn(user_id: int, message: str, reply: str, cards: list[ProductCard]) -> None:
    """Save one chat turn: the shopper's message, then the reply with its product cards."""
    cards_json = json.dumps([{"product_id": c.product_id, "name": c.name, "price": c.price} for c in cards])
    with get_db() as conn:
        conn.execute("INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
                     (user_id, message))
        conn.execute("INSERT INTO chat_messages (user_id, role, content, products_json) "
                     "VALUES (?, 'assistant', ?, ?)", (user_id, reply, cards_json))


def _saved_rows(conn: sqlite3.Connection, user_id: int, limit: int) -> list[sqlite3.Row]:
    rows = conn.execute(
        "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
    ).fetchall()
    return list(reversed(rows))


def _card_ids(products_json: str | None) -> list[str]:
    try:
        items = json.loads(products_json or "[]")
    except json.JSONDecodeError:
        return []
    return [i["product_id"] for i in items if isinstance(i, dict) and isinstance(i.get("product_id"), str)]


def agent_history(user_id: int) -> list[ChatTurn]:
    """The saved conversation, as the turns the agent reads before the new message."""
    with get_db() as conn:
        rows = _saved_rows(conn, user_id, HISTORY_FOR_AGENT)
    return [ChatTurn(role=r["role"], content=r["content"][:4000])
            for r in rows if r["role"] in ("user", "assistant")]


def record_view(user_id: int, product_id: str) -> bool:
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM catalogue WHERE product_id = ?", (product_id,)).fetchone():
            return False
        conn.execute("INSERT INTO product_views (user_id, product_id) VALUES (?, ?)", (user_id, product_id))
    return True


def last_viewed_product_id(user_id: int) -> str | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT product_id FROM product_views WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
        ).fetchone()
    return row["product_id"] if row else None


def last_search(user_id: int) -> str | None:
    """The shopper's most recent search (see _last_search)."""
    found = _last_search(user_id)
    return found[0] if found else None


def _last_search(user_id: int) -> tuple[str, list[str]] | None:
    """The shopper's most recent search and the product ids it showed: the last chat message
    whose reply showed two or more product cards (a question about one item, like
    "this in pink?", is not a search). Falls back to the last message that showed any card."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json FROM chat_messages WHERE user_id = ? "
            "ORDER BY id DESC LIMIT 60", (user_id,)
        ).fetchall()
    # Rows are newest first: an assistant reply with cards, then the user message before it.
    def question_before(i: int) -> str | None:
        return next((r["content"] for r in rows[i + 1:] if r["role"] == "user"), None)

    for min_cards in (2, 1):
        for i, r in enumerate(rows):
            if r["role"] == "assistant" and len(_card_ids(r["products_json"])) >= min_cards:
                question = question_before(i)
                # Clicking a welcome-back button ("Show me more styles like...") is not a new search.
                if question and not is_suggestion(question):
                    return question, _card_ids(r["products_json"])
    return None


def recalled_product(user_id: int) -> ProductDetail | None:
    """The item to recall when a shopper comes back: the last product they looked at, or else
    the top result of their last search. Read fresh from catalogue + inventory, so the price,
    description, sizes and stock are current."""
    product_id = last_viewed_product_id(user_id)
    if product_id is None:
        found = _last_search(user_id)
        product_id = found[1][0] if found and found[1] else None
    if product_id is None:
        return None
    products = load_products(ShopDeps(db_path=DB_PATH), [product_id])
    return products[0] if products else None


def stock_summary(p: ProductDetail) -> str:
    """Plain-English price, sizes and stock for one product, e.g. for the welcome-back message."""
    low = [f"{s.size} ({s.quantity} left)" for s in p.inventory if 0 < s.quantity <= LOW_STOCK_THRESHOLD]
    if not p.sizes_in_stock:
        return f"It's ${p.price:.2f} and is currently sold out in every size."
    text = f"It's ${p.price:.2f} and in stock in {', '.join(p.sizes_in_stock)}"
    if low:
        text += f" (running low: {', '.join(low)})"
    if p.sold_out_sizes:
        text += f"; sold out in {', '.join(p.sold_out_sizes)}"
    return text + "."


def is_suggestion(text: str) -> bool:
    """Not a new search: a welcome-back button, or a question about the item on screen
    ("do you have this in pink?", "is it in stock?")."""
    if text.startswith("Show me more styles like") or text == SIMILAR:
        return True
    return re.search(r"\b(this|it|that one|this one)\b", text, re.IGNORECASE) is not None


def _product_name(product_id: str | None) -> str | None:
    if not product_id:
        return None
    with get_db() as conn:
        row = conn.execute("SELECT name FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    return row["name"] if row else None


def _profile_summary(user_id: int) -> str:
    from customer_profile import build_profile  # Problem 9

    with get_db() as conn:
        profile, _, _ = build_profile(conn, user_id)
    return profile.summary()


def build_deps(user_id: int | None, page: PageContext | None) -> ShopDeps:
    """Everything the agent should know about who is chatting and where they are."""
    customer = load_customer(user_id) if user_id is not None else None
    page = page or PageContext()
    page = page.model_copy(update={"product_name": _product_name(page.product_id)})
    if customer:
        last_id = last_viewed_product_id(customer.user_id)
        customer = customer.model_copy(update={
            "last_viewed_product_id": last_id,
            "last_viewed_product_name": _product_name(last_id),
            "last_search": last_search(customer.user_id),
            "profile_summary": _profile_summary(customer.user_id),
        })
    recalled = recalled_product(customer.user_id) if customer else None
    return ShopDeps(db_path=DB_PATH, customer=customer, page=page, recalled_product=recalled)


# ---------- Endpoints ----------

class SavedMessage(BaseModel):
    role: str
    content: str
    products: list[ProductCard] = []
    created_at: str


class ChatMemory(BaseModel):
    customer: CustomerInfo
    messages: list[SavedMessage]
    last_viewed_product_id: str | None = None
    last_viewed_product_name: str | None = None
    last_search: str | None = None
    # Problem 8: the item recalled at login, with current price, description, sizes and stock.
    recalled_product: ProductCard | None = None
    welcome_back: str
    suggestions: list[str] = []


class ViewIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=200)


def _require_user(authorization: str | None) -> int:
    user_id = current_user_id(authorization)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Log in to see your saved chat.")
    return user_id


def welcome_message(customer: CustomerInfo, last_product: str | None, search: str | None,
                    returning: bool = True, recalled: ProductDetail | None = None) -> tuple[str, list[str]]:
    parts = [f"Welcome back, {customer.first_name}!" if returning else f"Hi, {customer.first_name}!"]
    if last_product:
        parts.append(f"I brought you back to the {last_product}, the last item you looked at.")
    elif recalled:
        parts.append(f"Last time I showed you the {recalled.name}.")
    if recalled:
        # Read from the database just now, so price and stock are current.
        parts.append(f"{recalled.description} {stock_summary(recalled)}")
    suggestions: list[str] = []
    if search:
        parts.append(f'Last time you asked: "{search}". Would you like to see more styles like that, '
                     "or should I suggest something similar?")
        suggestions = [f'Show me more styles like my last search: "{search}"', SIMILAR]
    elif last_product:
        parts.append("Would you like to see more styles like it, or should I suggest something similar?")
        suggestions = [f"Show me more styles like the {last_product}", SIMILAR]
    else:
        parts.append("What can I help you find today?")
    return " ".join(parts), suggestions


@router.get("/chat/history")
def chat_history(authorization: str | None = Header(default=None)) -> ChatMemory:
    """Saved chat for the logged-in shopper, plus where they left off."""
    user_id = _require_user(authorization)
    customer = load_customer(user_id)
    if customer is None:
        raise HTTPException(status_code=401, detail="Log in to see your saved chat.")
    with get_db() as conn:
        rows = _saved_rows(conn, user_id, HISTORY_FOR_WIDGET)
    deps = ShopDeps(db_path=DB_PATH)
    messages = []
    for r in rows:
        # Cards are rebuilt from the database so prices and stock are current, not as saved.
        products = load_products(deps, _card_ids(r["products_json"]))
        messages.append(SavedMessage(
            role=r["role"], content=r["content"], created_at=r["created_at"],
            products=[ProductCard(**p.model_dump(exclude={"search_tags"})) for p in products],
        ))
    last_id = last_viewed_product_id(user_id)
    last_name = _product_name(last_id)
    search = last_search(user_id)
    recalled = recalled_product(user_id)
    text, suggestions = welcome_message(customer, last_name, search, returning=bool(rows or last_id),
                                        recalled=recalled)
    return ChatMemory(customer=customer, messages=messages, last_viewed_product_id=last_id,
                      last_viewed_product_name=last_name, last_search=search,
                      recalled_product=ProductCard(**recalled.model_dump(exclude={"search_tags"})) if recalled else None,
                      welcome_back=text, suggestions=suggestions)


@router.post("/views", status_code=204)
def product_viewed(body: ViewIn, authorization: str | None = Header(default=None)) -> None:
    """Remember the product a logged-in shopper opened. Guests are not tracked."""
    user_id = current_user_id(authorization)
    if user_id is None:
        return None
    if not record_view(user_id, body.product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return None
